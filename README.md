# calendar-bot
A chatbot that you can answer any questions about your personal calendar.
The bot uses Google Calendar data downloaded from a separate script, `download_calendar.py`. Once your calendar is downloaded, you can use run the `bot.py` script to for calendar Q & A.

# CS 447 Demo Instructions HERE
## Instructions to run the demo 
1. unzip demo_files.zip
    - The slides are in `Calendar Bot Demo Slides.pdf`
    - The code and this README are in `calendar-bot-demo`, which contains:
        - The `.env` includes a GEMINI API key.
        - `sample_calendar.json` contains sample calendar data for the demo. Downloaded on Tuesday, May 28, 2024. The calendar content is described on slide 9.
        - `requirements_demo.txt` is a list of python libraries to install to run the code.
        - Google Calendar download related code can be found in `test_google_calendar_access.py` and `download_calendar.py`. See `download_calendar.py` for how we downloaded and preprocessed the calendar data saved in `sample_calendar.json`. You cannot run this code without Google Calendar Access credentials, which have not been provided for you. Instead, we provide the calendar data.
        - `bot.py` is the script to run the bot. The intent classification code is in `intent_classifier.py`. The date extraction code is in `date_extraction.py` and retrieval & vector index code is in `retrieval.py`
2. Navigate into the directory `calendar-bot-demo`
3. Create a `python=3.10` environment and install the requirements:
    ```bash
    conda create -n calendar-bot python=3.10 
    conda activate calendar-bot  
    pip install -r requirements_demo.txt
    ``` 
3. Run the bot with default settings and verbosity set at 2 (prints the response, detected intent, dates extracted, number of documents retrieved, and the details of the retrieved documents): ```python bot.py --verbose 2```


# General Instructions

## Setting up 

### 1. Python requirements
This chatbot was developed in a `python=3.10` environment. The requirements for the demo are in `requirements_demo.txt`.

```bash
conda create -n calendar-bot python=3.10 
conda activate calendar-bot  
pip install -r requirements_demo.txt
```

### 2. GOOGLE API KEY for Gemini
The chatbot uses the Gemini family of LLMs. If you don't have an API KEY to query these models:
1. Create one here: https://aistudio.google.com/app/apikey
2. Save it in a .env file like so
```
GOOGLE_API_KEY=<API_KEY>
```

### 3. Google Calendar data access
The chatbot answers questions about your own personal Google Calendar. This demo focuses on the conversational functionalities, not integration with other services. If you wish to use your own personal calendar data, you can need Google Calendar API access. If you are running the demo code, use the sample calendar data in `sample_calendar.json`.

#### Sample calendar data:
The file `sample_calendar.json` contains a calendar that you can use to test the chatbot. This file contains personal data and will be provided with the demo code.

#### Google Calendar API access instructions:
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
    - Download the JSON file for your credentials, move the file to the root of this repo and name it `credentials.json`.
5. Add your email as a test user in the app: https://stackoverflow.com/questions/75454425/access-blocked-project-has-not-completed-the-google-verification-process
6. Test your calendar access by running the script ```python test_google_calendar_access.py```. This will read your calendar and print the values of the `summary` and `startTime` fields for the next 10 events in the calendar.

## Usage
 
### 1. Download the calendar data
To download the your calendar data, run he calendar download script with the following command:  
```python download_calendar.py [options]```

#### Options
- **--calendar_path**: Specifies the path at which to save the calendar JSON file. Default is 'sample_calendar.json'.
- **-f, --filter**: Filter calendar events to keep keys: {['id', 'date', 'start', 'location', 'summary', 'description']} (**recommended**). Other keys are unnecessary for this app.
- **-n, --n_events**: Specify the max number events to download from the the calendar (default is 50).
- **-p, --past**: Retrieve past events (include last 2 weeks) (**recommended**).

Here is an example with recommended arguments:  
```python download_calendar.py --calendar_path "my_calendar.json" --filter --past --n_events 50```

If you did not set up Google Calendar API access to use your personal calendar, skip this step and use the sample data in the `sample_calendar.json` provided.

### 2. Chat with Gemini
Run the script with the following command:  
```python bot.py [options]```

#### Options
- **-p, --calendar_path**: Specifies the path from which to load the calendar JSON file. Default is 'sample_calendar.json'.
- **-a, --use_async**: Enable asynchronous operation for intent classification and date extraction.
- **-s, --stream**: Streams the calendar_qa response chunk by chunk (**LEAVE THIS OUT OR SET IT TO FALSE**).
- **-n, --top_n**: Specify the number of top documents to retrieve from the calendar (default is 5).
- **-f, --fields**: Specify the fields from the calendar to be indexed (default are "location", "summary", "description").
- **-v, --verbose**: Control the verbosity of the output:
  - `0`: Print only the response.
  - `1`: Print detected intent, number of documents retrieved, and dates extracted.
  - `2`: Additionally, print details of the retrieved documents.
  - `3`: Additionally, print processing time.

Here is an example:  
```python bot.py --calendar_path "sample_calendar.json" --use_async --top_n 5 --fields "location,summary,description" --verbose 1```

