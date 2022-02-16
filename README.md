# ELG adapted API for HeLI OTS 1.2

This git repository contains ELG adapted REST API 
for the HeLI OTS 1.1 language identifier 
(<http://urn.fi/urn:nbn:fi:lb-2021062801>, <https://zenodo.org/record/5890998#.Ye6bGhtBydY>, 
Apache licence 2.0, published Jan 22, 2022).

The language identifier implementation is a command-line program implemented 
in Java. It is contained in a single file, HeLI.jar, and it is called as a 
subprocess from the app.py (the ELG Flask app).

## Local development

First download the java application and place in this project's root directory
```
wget -q -O HeLI.jar https://zenodo.org/record/5890998/files/HeLI.jar?download=1
```
Run the development mode flask app

```
FLASK_ENV=development flask run --host 0.0.0.0 --port 8000
```

## Building the docker image

```
docker build -t heli-elg .
```

## Deploying the service

```
docker run -d -p <port>:8000 --init --memory="4g" --restart always heli-elg
```

## REST API

### Call pattern

#### URL

```
http://<host>:<port>/process
```

Replace `<host>` and `<port>` with the host name and port where the 
service is running.

#### HEADERS

```
Content-type : application/json
```

#### BODY

```
{
  "type":"text",
  "params":{...},   /* optional */ 
  "content": concatenated string of sentences, separated by newline `\n`

}

```

The `content` property contains a concatenated string by newline of language sentences to be identified. If blank string is given, API always return Finnish as default identified language.

#### RESPONSE

```
{
  "response":{
    "type":"annotations",
    "annotations":{
      "lid":[
        {
          "start":number,
          "end":number,
          "features":{ "lang3": str, "lang2: str, "confidence": float }
        }
      ]
    }
  }
}
```

The items in the `lid` list are at corresponding positions to the input 
of concatenated string in the `content`property of send request. 

### Response structure

- `start` and `end` (int)
  - the indices of the sentences in send request
- `lang3` (str)
  - ISO 639-3 code of the language
- `lang2` (str)
  - ISO 639-2 code of the language if available, otherwise null
- `confidence` (float)
  - confidence score of the language, log likelihood probability.
- `original_text` (optional, str)
  - optional original text

### Optional paremeters to add to body at top level

- `includeOrig` (bool, default=false)
  - true  : include original texts in the response structure
  - false : do not include original text
- `bestLangs` (int, default=10)
	- The number of top-scored languages
- `languageSet` (list, optional)
  - A list of 3-letter language codes to filter. If given, the identifier will only output the languages in the list.
- `languageMap` (dict, optional)
  - A dictionary object, that maps 2-letter language codes given by the identifier to other 2-letter language codes
  - Example: `{ "ms":"id" }`

### Example call

```
curl --location --request POST 'http://localhost:8001/process' \
--header 'Content-Type: application/json' \
--data-raw '{
"type":"text",
"params":{"includeOrig": "True","languageSet":["fin","swe","eng"]},
"content": "Suomi on kaunis maa\nGod morgon!\nThis is an English sentence"
}'
```

### Response should be

```
{
  "response": {
    "type": "annotations",
    "annotations": {
      "lid": [
        {
          "start": 0,
          "end": 19,
          "features": {
            "lang3": "fin",
            "lang2": "fi",
            "confidence": 3.6296403,
            "original_text": "Suomi on kaunis maa"
          }
        },
        {
          "start": 20,
          "end": 31,
          "features": {
            "lang3": "swe",
            "lang2": "sv",
            "confidence": 4.1419973,
            "original_text": "God morgon!"
          }
        },
        {
          "start": 32,
          "end": 59,
          "features": {
            "lang3": "eng",
            "lang2": "en",
            "confidence": 3.242215,
            "original_text": "This is an English sentence"
          }
        }
      ]
    }
  }
}
```
