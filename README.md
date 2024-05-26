# calendar-bot
A chatbot that you can answer any questions about your personal calendar.
The bot uses Google Calendar data downloaded from a separate script, `download_calendar.py`. Once your calendar is downloaded, you can use run the `bot.py` script to for calendar Q & A.

## Setting up 

### 1. Python requirements
This chatbot was developed in a `python > 3.10` environment. The requirements for the demo are in `requirements_demo.txt`.

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
- **-n, --top_n**: Specify the number of top documents to retrieve from the calendar (default is 3).
- **-f, --fields**: Specify the fields from the calendar to be indexed (default are "location", "summary", "description").
- **-v, --verbose**: Control the verbosity of the output:
  - `0`: Print only the response.
  - `1`: Print detected intent, number of documents retrieved, and dates extracted.
  - `2`: Additionally, print processing time.
  - `3`: Additionally, print details of the retrieved documents.

Here is an example:  
```python bot.py --calendar_path "sample_calendar.json" --use_async --top_n 5 --fields "location,summary,description" --verbose 1```
