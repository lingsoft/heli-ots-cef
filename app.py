

import os
from elg import FlaskService
from elg.model import Failure, TextRequest, AnnotationsResponse
from elg.model.base import StandardMessages


from subprocess import Popen, PIPE
import threading
import unicodedata
import re

import languagecodes

import logging
logging.basicConfig(level=logging.DEBUG)


class LidHeli(FlaskService):

	# Remove control characters from a string:
	def remove_control_characters(self, s):
			return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

	def process_text(self, request: TextRequest):

			global language_set, n_best_lang
			# handle some params
			langmap, orig = None, None
			params = request.params
			if params:
				orig = params.get('includeOrig', False)
				language_set = params.get('languageSet', None)
				langmap = params.get('languageMap', None)
				n_best_lang = params.get('bestLangs', 10)

			texts = request.content
			output = list()
			offset = 0
			with lid_lock:
				for id, l in enumerate(texts.split('\n')):
						in_text = self.remove_control_characters(l.replace("\r", "").replace(
								"\n", " ").replace("\t", " ").replace("\u2028", " ").replace("\u2029", " ")) + "\n"
						#in_text = remove_control_characters(l.replace("\r","").replace("\n", " ").replace("\t", " ")) + "\n"
						process.stdin.write(in_text.encode("utf-8"))
						process.stdin.flush()
						lang_list = []
						# read output until there's an empty line:
						while True:
								raw_line = process.stdout.readline().decode("utf-8").strip("\n")
								if len(raw_line) and raw_line != "xxx":
										m = re.search("^\[(.*)\],([0-9\.]+)", raw_line)
										if m:
												langs = m.group(1).split(", ")
												score = m.group(2)
												for l3 in langs:
														l2 = languagecodes.iso_639_alpha2(l3)

														if langmap:
																if l2 in langmap and isinstance(langmap[l2], str):
																		l2 = langmap[l2]
																		l3 = languagecodes.iso_639_alpha3(l2)

														lang_list.append(
																{"lang2": l2, "lang3": l3, "score": float(score)})
								else:  # end of output
										break

						lang2 = None
						lang3 = None
						conf = 0
						# print('lang list', lang_list)
						if len(lang_list):
								lang2 = lang_list[0]["lang2"]
								lang3 = lang_list[0]["lang3"]
								# difference of log-probabilities between two best-scoring languages
								if len(lang_list) > 1:
										conf = lang_list[1]["score"] - lang_list[0]["score"]

						if language_set:
								# default to first language in language_set:
								if len(language_set):
										lang3 = language_set[0]
										lang2 = languagecodes.iso_639_alpha3(lang3)

										# pick the best returned language that is in language_set:
										found = False
										for i in range(len(lang_list)):
												lg = lang_list[i]
												if lg["lang3"] in language_set:
														found = True
														lang2 = lg["lang2"]
														lang3 = lg["lang3"]
														conf = lg["score"]
														# if i > 0:  # not picking the best language => output zero confidence
														#     conf = 0  # lang_list[0]["score"]-lg["score"]
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
								"features": {"lang3": lang3, "lang2": lang2, "confidence": conf}
						}
						offset = offset + len(l) + 1

						if orig:
							clf_obj["features"]["original_text"] = l
						output.append(clf_obj)
			try:
				return AnnotationsResponse(annotations={"language_identification": output})
			except Exception as e:
				detail = {'server error': str(e)}
				error = StandardMessages.generate_elg_service_internalerror(
						detail=detail)
				return Failure(errors=[error])


lid_heli_service = LidHeli("lid-heli-service")
app = lid_heli_service.app

# Global variables for the service:
process = None
lid_lock = threading.Lock()
n_best_lang = 10
language_set = None

inDev = os.getenv('FLASK_ENV')


@app.before_first_request
def setup():
		global process
		app.logger.info("before_first_request")
		#process = Popen(['java', '-jar', 'HeLI.jar', '-c'], stdin=PIPE, stdout=PIPE)

		if inDev:
			if language_set:
					process = Popen(['java', '-jar', 'HeLI.jar', '-l', ",".join(language_set),
													'-t', str(n_best_lang)], stdin=PIPE, stdout=PIPE)
			else:
					process = Popen(['java', '-jar', 'HeLI.jar', '-t',
													str(n_best_lang)], stdin=PIPE, stdout=PIPE)
		else:  # in Docker
			if language_set:
					process = Popen(['/java/bin/java', '-XX:+UseG1GC', '-Xms2g', '-Xmx2g', '-jar', 'HeLI.jar', '-l', ",".join(language_set),
													'-t', str(n_best_lang)], stdin=PIPE, stdout=PIPE)
			else:
					process = Popen(['/java/bin/java', '-XX:+UseG1GC', '-Xms2g', '-Xmx2g', '-jar', 'HeLI.jar', '-t',
													str(n_best_lang)], stdin=PIPE, stdout=PIPE)


# test request:
# curl -d '{"type":"structuredText", "params": {"includeOrig":"True", "languageSet":["fin","swe","eng"]} ,"texts": [{"content":"Suomi on kaunis mää"}, {"content": "The President just came"}]}' -H "Content-Type: application/json" -X POST http://localhost:8000/process
