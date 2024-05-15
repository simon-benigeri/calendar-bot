from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime
import json

# Path to your credentials JSON file
CREDENTIALS_FILE = "credentials.json"

# Specify the scopes: URL that indicates Google Calendar API
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def authenticate_google_calendar():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    return creds


def format_date_description(events):
    """Add a text description of the date, 
        e.g.,   'Sunday May 12, 10:30AM-12:30PM'
                'Saturday June 01, 10:00PM - Sunday June 02, 10:00AM'.
    """
    for event in events:
        start_dt = datetime.datetime.fromisoformat(event["start"]["dateTime"])
        end_dt = datetime.datetime.fromisoformat(event["end"]["dateTime"])
        
        # Check if start and end are on different days
        if start_dt.date() == end_dt.date():
            event_date = start_dt.strftime('%A %B %d, %I:%M%p')
            event_end_time = end_dt.strftime('%I:%M%p')
            date = f"{event_date}-{event_end_time}"
        else:
            event_date = start_dt.strftime('%A %B %d, %I:%M%p')
            event_end_date = end_dt.strftime('%A %B %d, %I:%M%p')
            date = f"{event_date} - {event_end_date}"
        
        event['date'] = date
    
    return events


def filter_event_keys(events, keys_to_remove):
    filtered_events = []
    for event in events:
        filtered_event = {key: value for key, value in event.items() if key not in keys_to_remove}
        filtered_events.append(filtered_event)
    return filtered_events

# # Example usage
# keys_to_remove = ['start', 'end', 'creator', 'organizer']
# filtered_events = filter_event_keys(formatted_events, keys_to_remove)


def get_calendar_events():
    creds = authenticate_google_calendar()
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    print("Getting the upcoming events")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=30,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        print("No upcoming events found.")

    events = format_date_description(events)

    for event in events:
        # start = event["start"].get("dateTime", event["start"].get("date"))
        event_date = event["date"]
        print(event_date, event["summary"])

    return events


if __name__ == "__main__":
    # Save events to a JSON file
    events = get_calendar_events()
    print(f"Retrieving {len(events)} events.")
    with open("my_calendar_data.json", "w") as f:
        json.dump(events, f)
