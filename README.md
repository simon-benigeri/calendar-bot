# calendar-bot
A conversational UI to ask questions about your weekly calendar and to update your calendar.

## Setup guide

### 1. GOOGLE API KEY for Gemini
1. Create one here: https://aistudio.google.com/app/apikey
2. Save it in a .env file like so
```
GOOGLE_API_KEY=<API_KEY>
```

### 2. Google calendar API access (ignore this we are doing a zoom to walk through it)
1. Go to https://cloud.google.com/endpoints/docs/openapi/enable-api#console (make sure you are logged in) and click on `Go to APIs & Services1
 Instructions: Set Up Google Cloud Project
2. Create a Google Cloud project if you don't have one:
    - Visit the Google Cloud Console.
    - Click on "New Project", give it a name, and create it.
3. Enable the Google Calendar API:
    - Navigate to the "APIs & Services > Library".
    - Search for "Google Calendar API" and enable it for your project.
4. Create credentials:
    - Go to "APIs & Services > Credentials".
    - Click on “Create Credentials” and choose “OAuth client ID”.
    - Configure the consent screen if prompted.
    - Set the application type to "Desktop app" and give it a name.
    - Download the JSON file for your credentials.
5. Add your email as a test user in the app: https://stackoverflow.com/questions/75454425/access-blocked-project-has-not-completed-the-google-verification-process


### 3. Setup your python environment
`conda create -n calendar-bot python=3.10`  
`conda activate calendar-bot`  
`pip install -r requirements.txt`  


### 4. Install Ollama and download the model mistral:instruct (not required for Gemini chat)
1. Install Ollama from this link: https://ollama.com/download
2. Open a terminal and run: `ollama run mistral:instruct`. Once the model is downloaded you can close the process.
 

### 5. Download the calendar data
To download the calendar data:  
`python calendar_utils.py`

```
-f is a flag to filter the calendar data
-n provides max number of events to retrieve (default value is 50)
-p includes past events, from 2 weeks ago
```

To download the calendar data, filtered, with up to 50 events, including the past 2 weeks:  
`python calendar_utils.py -f -p -n 50`

### 6. Start chatting
<!-- 1. Start Ollama on your local machine
2. To start chatting with gemini:  
`python retrieval_bot.py -g` or `python retrieval_bot.py -g -v` if you want the intent classifier output. -->
1. To start chatting with gemini:  
`python bot.py -g` or `python bot.py -g -v` if you want the intent classifier output.
```
-g use gemini
-v print outputs for intent classifier and date extractor
-n provides max number of events to retrieve (default value is 3), e.g. -n 5
```
2. To start chatting with mistral:instruct on Ollama:  
    1. Start Ollama on your local machine
    2. `python bot.py` or `python bot.py -v` if you want the intent classifier output.

