# ELG API for HeLI-OTS

This git repository contains [ELG compatible](https://european-language-grid.readthedocs.io/en/stable/all/A3_API/LTInternalAPI.html)  Flask based REST API for the HeLI-OTS language identifier.

[HeLI-OTS 1.3](https://zenodo.org/record/6077089) is the off-the-shelf language identifier with 
language models for 200 languages. HeLI-OTS is written in Java, and published under Apache licence 2.0.
Original authors are Tommi Jauhiainen and Heidi Jauhiainen from the University of Helsinki.

This ELG API was developed in EU's CEF project: [Microservices at your service](https://www.lingsoft.fi/en/microservices-at-your-service-bridging-gap-between-nlp-research-and-industry)

## Local development

First download the java application and place in this project's root directory
```
wget -q -O HeLI.jar https://zenodo.org/record/6077089/files/HeLI.jar?download=1
```

Setup virtualenv, dependencies
```
python3 -m venv heli-venv
source heli-venv/bin/activate
python3 -m pip install -r requirements.txt
```

Run the development mode flask app
```
FLASK_ENV=development flask run --host 0.0.0.0 --port 8000
```

## Run tests for a running app

```
python3 -m unittest -v
```

## Building the docker image

```
docker build -t heli-elg .
```

Or pull directly ready-made image `docker pull lingsoft/heli-ots:tagname`.

## Deploying the service

```
docker run -d -p <port>:8000 --init --memory="4g" --restart always heli-elg
```

## Example call

```
curl -H "Content-Type: application/json" -d @text-request.json http://localhost:8000/process
```

### Text request

```json
{
  "type":"text",
  "params":{"includeOrig": true, "languageSet":["fin","swe","eng"]},
  "content": "Suomi on kaunis maa\nMitä tänään syötäisiin?\nGod morgon!\nThis is an English sentence\nBoris Johnson left London\nThis is second sentence in English\nOlen asunnut Suomessa noin 10 vuotta"
}
```

The `content` property contains a concatenated string by newline of language sentences to be identified. 
If blank string is given, API always return Finnish as default identified language.

Optional paremeters to add to body at top level

- `includeOrig` (bool, default=false)
  - true  : include original texts in the response structure
  - false : do not include original text
- `languageSet` (list, optional)
  - A list of 3-letter or 2-letter language codes to filter. If given, the identifier will only output the languages in the list.


### Response should be

- `start` and `end` (int)
  - the indices of the sentences in send request
- `lang3` (str)
  - ISO 639-3 code of the language
- `lang2` (str)
  - ISO 639-1 code of the language if available, otherwise null
- `confidence` (float)
  - calculated as the difference of log-probabilities of the two top-scoring languages
  - may be zero when the `languageSet` parameter is used and the identified language is not in `languageSet`, or when `languageSet` consists of only one language.
- `original_text` (optional, str)
  - optional original text

```json
{
  "response":{
    "type":"annotations",
    "annotations":{
      "fin":[
        {
          "start":0,
          "end":19,
          "features":{
            "lang3":"fin",
            "lang2":"fi",
            "confidence":3.1124437,
            "original_text":"Suomi on kaunis maa"
          }
        },
        {
          "start":20,
          "end":43,
          "features":{
            "lang3":"fin",
            "lang2":"fi",
            "confidence":3.351351,
            "original_text":"Mitä tänään syötäisiin?"
          }
        },
        {
          "start":145,
          "end":181,
          "features":{
            "lang3":"fin",
            "lang2":"fi",
            "confidence":3.5109267,
            "original_text":"Olen asunnut Suomessa noin 10 vuotta"
          }
        }
      ],
      "swe":[
        {
          "start":44,
          "end":55,
          "features":{
            "lang3":"swe",
            "lang2":"sv",
            "confidence":3.8769577,
            "original_text":"God morgon!"
          }
        }
      ],
      "eng":[
        {
          "start":56,
          "end":83,
          "features":{
            "lang3":"eng",
            "lang2":"en",
            "confidence":2.9322097,
            "original_text":"This is an English sentence"
          }
        },
        {
          "start":84,
          "end":109,
          "features":{
            "lang3":"eng",
            "lang2":"en",
            "confidence":4.5815454,
            "original_text":"Boris Johnson left London"
          }
        },
        {
          "start":110,
          "end":144,
          "features":{
            "lang3":"eng",
            "lang2":"en",
            "confidence":2.883938,
            "original_text":"This is second sentence in English"
          }
        }
      ]
    }
  }
}
```

## Notes
- If there are partial or full invalid language codes given in `languageSet`, they are included in warnings property of the response. For example

Call:

```shell
curl -H "Content-Type: application/json" -d @text-request-invalid.json http://localhost:8000/process
```
Response:

```json
{
  "response": {
    "type": "annotations",
    "warnings": [
      {
        "code": "elg.request.parameter.languageSet.partial.values.invalid",
        "params": [
          "invalid,wrong"
        ],
        "text": "There are some invalid language codes: {0}"
      }
    ],
    "annotations": {
      "eng": [
        {
          "start": 0,
          "end": 29,
          "features": {
            "lang3": "eng",
            "lang2": "en",
            "confidence": 2.5944998,
            "original_text": "This is a sentence in English"
          }
        }
      ],
      "fin": [
        {
          "start": 30,
          "end": 66,
          "features": {
            "lang3": "fin",
            "lang2": "fi",
            "confidence": 3.5109267,
            "original_text": "Olen asunnut Suomessa noin 10 vuotta"
          }
        }
      ]
    }
  }
}
```