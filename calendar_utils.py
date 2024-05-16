from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import datetime
import json
import argparse

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


def filter_event_keys(events, keys_to_keep):
    filtered_events = []
    for event in events:
        filtered_event = {key: event.get(key, "") for key in event if key in keys_to_keep}
        filtered_events.append(filtered_event)
    return filtered_events


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
    parser = argparse.ArgumentParser(
        description="Download calendar data."
    )
    parser.add_argument(
        "-f",
        "--filter",
        action="store_true",
        help=f"Filter calendar events to keep keys: {['id', 'date', 'location', 'summary', 'description']}.",
    )

    args = parser.parse_args()
    # Save events to a JSON file
    events = get_calendar_events()
    print(f"Retrieving {len(events)} events.")
    path = "my_calendar_data.json"
    keys_to_keep = ['id', 'date', 'location', 'summary', 'description']
    if args.filter:
        events = filter_event_keys(events, keys_to_keep)
        path = "my_calendar_data_filtered.json"
    with open(path, "w") as f:
        json.dump(events, f)
