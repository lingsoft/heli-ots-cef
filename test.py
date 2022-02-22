import unittest
import json
import requests


class TestResponseStucture(unittest.TestCase):
    base_url = 'http://localhost:8001/process'

    texts = 'Suomi on kaunis maa\nMitä tänään syötäisiin?\
            \nGod morgon!\nThis is an'\
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


if __name__ == '__main__':
    unittest.main()
