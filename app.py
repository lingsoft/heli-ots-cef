import os

from elg import FlaskService
from elg.model import Failure, TextRequest, AnnotationsResponse
from elg.model.base import StandardMessages, StatusMessage

from subprocess import Popen, PIPE
import threading
import unicodedata
import re
from collections import defaultdict

import languagecodes

import logging

logging.basicConfig(level=logging.DEBUG)


class LidHeli(FlaskService):

    # Remove control characters from a string:
    def remove_control_characters(self, s):
        return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

    def process_text(self, request: TextRequest):

        global language_set
        # handle some params
        orig, warning_msg = None, None
        params = request.params
        if params:
            orig = params.get("includeOrig", False)
            if not isinstance(orig, bool):
                invalid_param_msg = 'includeOrig parameter requires boolean type'
                error = StandardMessages.\
                    generate_elg_service_internalerror(
                        params=[invalid_param_msg])
                return Failure(errors=[error])

            language_set = params.get("languageSet", None)
            # Sometime incorrect language codes were given,
            # filter only valid ones
            # if all language are invalid, set None.
            if language_set:
                if not isinstance(language_set, list):
                    invalid_param_msg = 'LanguageSet parameter requires list type'
                    error = StandardMessages.\
                        generate_elg_service_internalerror(
                            params=[invalid_param_msg])
                    return Failure(errors=[error])

                invalid_lang_codes = [
                    lang for lang in language_set
                    if not languagecodes.iso_639_alpha3(lang)
                ]

                if len(invalid_lang_codes) == 0:
                    language_set = [
                        languagecodes.iso_639_alpha3(lang)
                        for lang in language_set
                    ]
                elif len(invalid_lang_codes) > 0 and len(
                        invalid_lang_codes) < len(language_set):
                    warning_params = ','.join(invalid_lang_codes)
                    warning_msg = StatusMessage(
                        code='elg.request.parameter.invalid',
                        params=[warning_params],
                        text='There are some invalid language codes: {0}')
                    language_set = [
                        languagecodes.iso_639_alpha3(lang)
                        for lang in language_set
                        if languagecodes.iso_639_alpha3(lang)
                    ]

                elif len(invalid_lang_codes) == len(language_set):
                    warning_params = ','.join(invalid_lang_codes)
                    warning_msg = StatusMessage(
                        code='elg.request.parameter.invalid',
                        params=[warning_params],
                        text='All language codes given are invalid: {0}')

                    language_set = None

        texts = request.content
        output = defaultdict(list)
        offset = 0
        with lid_lock:
            for id, l in enumerate(texts.split("\n")):
                in_text = (self.remove_control_characters(
                    l.replace("\r", "").replace("\n", " ").replace(
                        "\t", " ").replace("\u2028", " ").replace(
                            "\u2029", " ")) + "\n")
                process.stdin.write(in_text.encode("utf-8"))
                process.stdin.flush()
                lang_list = []
                # read output until there's an empty line:
                while True:
                    raw_line = process.stdout.readline().decode("utf-8").strip(
                        "\n")
                    if len(raw_line) and raw_line != "xxx":
                        m = re.search(r"^\[(.*)\],([0-9\.]+)", raw_line)
                        if m:
                            langs = m.group(1).split(", ")
                            score = m.group(2)
                            for l3 in langs:
                                l2 = languagecodes.iso_639_alpha2(l3)

                                lang_list.append({
                                    "lang2": l2,
                                    "lang3": l3,
                                    "score": float(score)
                                })
                    else:  # end of output
                        break
                lang2 = None
                lang3 = None
                conf = 0

                if len(lang_list):
                    lang2 = lang_list[0]["lang2"]
                    lang3 = lang_list[0]["lang3"]
                    # difference of log-probabilities
                    # between two best-scoring languages
                    if len(lang_list) > 1:
                        conf = lang_list[1]["score"] - lang_list[0]["score"]

                if language_set:
                    # default to first language in language_set:
                    if len(language_set):
                        lang3 = language_set[0]
                        lang2 = languagecodes.iso_639_alpha2(lang3)

                        # pick the best returned language
                        #  that is in language_set:
                        found = False
                        for i in range(len(lang_list)):
                            lg = lang_list[i]
                            if lg["lang3"] in language_set:
                                found = True
                                lang2 = lg["lang2"]
                                lang3 = lg["lang3"]
                                conf = lg["score"]
                                # if not picking the best language
                                # => output zero confidence
                                if i > 0:
                                    conf = 0  # lang_list[0]["score"]-lg["score"]
                                break
                        if not found:
                            conf = 0

                    # empty language_set => None
                    else:
                        lang2 = None
                        lang3 = None
                        conf = 0

                clf_obj = {
                    "start": offset,
                    "end": offset + len(l),
                    "features": {
                        "lang3": lang3,
                        "lang2": lang2,
                        "confidence": conf
                    },
                }
                offset = offset + len(l) + 1

                if orig:
                    clf_obj["features"]["original_text"] = l

                output[lang3].append(clf_obj)
        try:
            if warning_msg:
                return AnnotationsResponse(annotations=output,
                                           warnings=[warning_msg])
            else:
                return AnnotationsResponse(annotations=output)

        except Exception as e:
            error = StandardMessages.generate_elg_service_internalerror(
                params=[str(e)])
            return Failure(errors=[error])


lid_heli_service = LidHeli("lid-heli-service")
app = lid_heli_service.app

# Global variables for the service:
process = None
lid_lock = threading.Lock()
n_best_lang = 10
language_set = None

inDev = os.getenv("FLASK_ENV")


@app.before_first_request
def setup():
    global process
    global language_set
    global n_best_lang

    app.logger.info("before_first_request")

    if inDev:
        if language_set:
            process = Popen(
                [
                    "java",
                    "-jar",
                    "HeLI.jar",
                    "-l",
                    ",".join(language_set),
                    "-t",
                    str(n_best_lang),
                ],
                stdin=PIPE,
                stdout=PIPE,
            )
        else:
            process = Popen(
                ["java", "-jar", "HeLI.jar", "-t",
                 str(n_best_lang)],
                stdin=PIPE,
                stdout=PIPE,
            )
    else:  # in Docker
        if language_set:
            process = Popen(
                [
                    "/java/bin/java",
                    "-XX:+UseG1GC",
                    "-Xms2g",
                    "-Xmx2g",
                    "-jar",
                    "HeLI.jar",
                    "-l",
                    ",".join(language_set),
                    "-t",
                    str(n_best_lang),
                ],
                stdin=PIPE,
                stdout=PIPE,
            )
        else:
            process = Popen(
                [
                    "/java/bin/java",
                    "-XX:+UseG1GC",
                    "-Xms2g",
                    "-Xmx2g",
                    "-jar",
                    "HeLI.jar",
                    "-t",
                    str(n_best_lang),
                ],
                stdin=PIPE,
                stdout=PIPE,
            )
