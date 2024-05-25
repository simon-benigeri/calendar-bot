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
<!-- 2. Select your project linked to the Gemini credits. If you do not have a project, create a project:
    First go to the dropdown menu to select projects
    ![alt text](assets/google_cloud_select_project.png)
    ![alt text](assets/google_cloud_create_project2.png)
    Here is an example, with project `test-project`. No need to select an organization. Click create.
    ![alt text](assets/google_cloud_create_project3.png)
If you do have a project, select it.
3. Click on `+ ENABLE APIS AND SERVICES` near the top of the screen
    ![alt text](assets/Enable_API.png)
    ![alt text](assets/search_calendar.png)
4. Once you are on the Google Calendar API page for your project, you need to create credentials for that API
    Click MANAGE
    ![alt text](assets/google_calendar_api.png)
    Click CREDENTIALS and then + CREATE CREDENTIALS
    ![alt text](assets/credentials.png)
    Select OAuth client ID (required user to authenticate so that your app can access the google calendar user's data).
    For Application type, select Desktop app. Choose whatever name you want. Click create. Download the JSON in the popup menu. -->


### 3. Setup your python environment
`conda create -n calendar-bot python=3.10`  
`conda activate calendar-bot`  
`pip install -r requirements.txt`  


### 4. Install Ollama and download the model mistral:instruct
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

