import unittest
import json
import requests
import languagecodes


class TestResponseStucture(unittest.TestCase):
    base_url = 'http://localhost:8000/process'

    texts = 'Suomi on kaunis maa\nMitä tänään syötäisiin?\
            \nTyvärr, jag kan inte engelska!\nThis is an'\
            ' English sentence\nBoris Johnson left London\
            \nThis is second sentence in'\
            ' English\nOlen asunnut Suomessa noin 10 vuotta'

    params = {"includeOrig": "True", "languageSet": ["fin", "swe", "eng"]}

    payload = json.dumps({"type": "text", "params": params, "content": texts})

    headers = {'Content-Type': 'application/json'}

    def test_api_response_status_code(self):
        """Should return status code 200
        """

        status_code = requests.post(self.base_url,
                                    headers=self.headers,
                                    data=self.payload).status_code
        self.assertEqual(status_code, 200)

    def test_valid_api_response(self):
        """Return response should not be empty
        """

        response = requests.post(self.base_url,
                                 headers=self.headers,
                                 data=self.payload).json()['response']
        self.assertNotEqual(response, None)

    def test_api_response_type(self):
        """Should return ELG annotation response type
        """
        response = requests.post(self.base_url,
                                 headers=self.headers,
                                 data=self.payload).json()['response']
        self.assertEqual(response.get('type'), 'annotations')

    def test_api_response_content(self):
        """Annotation response should contain only three keys fin,swe,eng
        """
        response = requests.post(self.base_url,
                                 headers=self.headers,
                                 data=self.payload).json()['response']
        self.assertEqual(len(response['annotations'].keys()), 3)
        for lang in self.params['languageSet']:
            self.assertIn(lang, response['annotations'].keys())

    def test_api_response_content_offset(self):
        """Annotation response of Finnish input sentence should
        contain three objects with corresponding correct offsets
        """
        response = requests.post(self.base_url,
                                 headers=self.headers,
                                 data=self.payload).json()['response']
        fin_result = response['annotations']['fin']
        self.assertEqual(len(fin_result), 3)

        for result in fin_result:
            self.assertEqual(
                result['start'],
                self.texts.find(result['features']['original_text']))
            self.assertEqual(
                result['end'],
                result['start'] + len(result['features']['original_text']))

    def test_api_response_invalid_or_missing_languageset(self):
        """Even though wrong languageset parameter are given,
        Annotation response of each sentence should
        return correct language codes: for example for Finnish sentences,
        fin for lang3, and fi for lang2.
        """
        expected_langs = (('fin', 'fi'), ('swe', 'sv'), ('eng', 'en'))

        # make invalid languagetset
        local_params = {k: v for k, v in self.params.items()}
        local_params['languageSet'] = ['invalid'] * len(expected_langs)
        # local_params['languageSet'] = ['swe', 'invalid', 'vi']
        local_payload = json.dumps({
            "type": "text",
            "params": local_params,
            "content": self.texts
        })

        response = requests.post(self.base_url,
                                 headers=self.headers,
                                 data=local_payload).json()['response']
        results = {}
        # print(response)
        for lang3, lang2 in expected_langs:
            results[lang3] = response['annotations'][lang3]

        for l3, res_obj in results.items():
            for res in res_obj:
                self.assertEqual(res['features']['lang3'], l3)
                self.assertEqual(res['features']['lang2'],
                                 languagecodes.iso_639_alpha2(l3))


if __name__ == '__main__':
    unittest.main()
