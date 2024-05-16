import json
from datetime import datetime, timedelta
import dateparser

from typing import List, Dict

from rank_bm25 import BM25Okapi
import nltk
from nltk.corpus import stopwords
from nltk.util import ngrams

nltk.download("punkt")
nltk.download("stopwords")


def get_next_weekday(start_date, weekday):
    """
    Given a start date and a weekday, calculate the date of the next occurrence of that weekday.
    """
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return start_date + timedelta(days_ahead)


def find_weekdays_in_string(query):
    # List of all weekdays
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    return [day for day in weekdays if day.lower() in query.lower()]


def extract_date(query, date_format="%A %B %d"):
    today = datetime.now()

    # Lowercase the query to handle case insensitivity
    query = query.lower()

    found_weekdays = find_weekdays_in_string(query)

    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    if found_weekdays:
        for i, day in enumerate(weekdays):
            if day in query:
                # Check if 'next' is explicitly mentioned to avoid confusion
                if "next" in query:
                    next_day_date = get_next_weekday(today, i)
                    return [next_day_date.strftime(date_format)]
                elif "every" in query:
                    dates = []
                    current_date = today
                    # Collect next 5 occurrences starting today if it is the day
                    for _ in range(5):
                        if current_date.weekday() != i:
                            current_date = get_next_weekday(current_date, i)
                        dates.append(current_date.strftime(date_format))
                        current_date += timedelta(days=7)  # Move to the next week
                    return dates
                else:
                    # Return today if today matches the day and it's not specified as 'next'
                    if today.weekday() == i:
                        return [today.strftime(date_format)]
                    else:
                        next_day_date = get_next_weekday(today, i)
                        return [next_day_date.strftime(date_format)]
    else:
        if "today" in query:
            return [today.strftime(date_format)]
        elif "tomorrow" in query:
            tomorrow = today + timedelta(days=1)
            return [tomorrow.strftime(date_format)]
        elif "this weekend" in query:
            start_weekend = today + timedelta(
                (5 - today.weekday()) % 7
            )  # Calculate next Saturday
            end_weekend = start_weekend + timedelta(days=1)  # Next Sunday
            return [
                start_weekend.strftime(date_format),
                end_weekend.strftime(date_format),
            ]
        elif "next week" in query:
            start_next_week = today + timedelta((7 - today.weekday()) % 7)
            week_dates = [start_next_week + timedelta(days=i) for i in range(7)]
            return [date.strftime(date_format) for date in week_dates]

    date = dateparser.parse(query, settings={"PREFER_DATES_FROM": "future"})
    if date:
        return [date.strftime(date_format)]
    else:
        return []


# def append_dates_to_query(query):
#     # Extract dates from the query
#     dates = extract_date(query)

#     # Append extracted dates to the query, if any
#     if dates:
#         updated_query = f"{query} on {' and '.join(dates)}"
#     else:
#         updated_query = query

#     return updated_query


def bm25_retrieve_from_json(docs, query, fields, n_gram=1, top_n=5):
    # Extract dates
    extracted_dates = extract_date(query)

    # Tokenization of documents
    tokenized_docs = [
        tokenize(
            "\n".join(
                str(doc[field])
                for field in fields
                if field in doc and field not in ["date", "start"]
            ),
            n=n_gram,
        )
        for doc in docs
    ]
    bm25 = BM25Okapi(tokenized_docs)

    # Tokenization of the query
    tokenized_query = tokenize(query)

    # Compute BM25 scores
    bm25_scores = bm25.get_scores(tokenized_query)

    # Calculate scores and add to docs
    for doc, bm25_score in zip(docs, bm25_scores):
        date_score = (
            1
            if any(
                extracted_date in doc.get("date", "")
                for extracted_date in extracted_dates
            )
            else 0
        )
        doc["date_score"] = date_score
        doc["bm25_score"] = bm25_score

    # First, retrieve all documents with date_score greater than 1
    retrieved_docs = [doc for doc in docs if doc["date_score"] > 0]

    # If there are not enough documents retrieved, fill up the rest with those having the highest BM25 scores
    if len(retrieved_docs) < top_n:
        remaining_docs_needed = top_n - len(retrieved_docs)
        remaining_docs = [
            doc
            for doc in sorted(docs, key=lambda doc: doc["bm25_score"], reverse=True)
            if doc not in retrieved_docs
        ][:remaining_docs_needed]
        retrieved_docs.extend(remaining_docs)

    retrieved_docs = sorted(retrieved_docs, key=lambda doc: doc.get("start", ""))

    # Drop the 'start' field from each document
    for doc in retrieved_docs:
        doc.pop(
            "start", None
        )  # Safely remove the 'start' field without causing an error if it's missing

    return retrieved_docs


def tokenize(text, n=1):
    # Tokenize the text
    words = nltk.word_tokenize(text.lower())

    # Filter out stopwords
    filtered_words = [word for word in words if word not in stopwords.words("english")]

    # Calculate n if not provided, assuming the max length for a phrase like "Saturday May 18"
    if n is None:
        n = len(filtered_words)

    # Generate unigrams and up to n-grams
    all_ngrams = []
    for i in range(1, n + 1):
        generated_ngrams = ngrams(filtered_words, i)
        all_ngrams.extend([" ".join(gram) for gram in generated_ngrams])

    return all_ngrams


def retrieve_docs(
    query: str,
    docs=List[Dict],
    n_gram=3,
    top_n=3,
    fields=["id", "date", "start", "location", "summary", "description"],
) -> Dict:
    extracted_dates = extract_date(query)
    relevant_docs = bm25_retrieve_from_json(
        docs, query, fields, n_gram=n_gram, top_n=top_n
    )
    response = {
        "query": query,
        "n_gram": n_gram,
        "top_n": top_n,
        "fields": fields,
        "extracted_dates": extracted_dates,
        "relevant_docs": relevant_docs,
    }
    return response


if __name__ == "__main__":

    calendar = json.load(open("my_calendar_data_filtered.json"))

    # # Example cases
    queries = [
        "What's happening Wednesday?",
        "What's happening next Monday?",
        "Remind me every Tuesday",
        "Schedule for this weekend",
        "What's happening today?",
        "Meet me tomorrow",
        "Let's plan for this weekend",
        "Schedule for next week",
    ]

    docs = calendar

    fields = ["id", "date", "start", "location", "summary", "description"]
    n_gram = 3
    top_n = 3
    for idx, query in enumerate(queries):
        response = retrieve_docs(query, docs, n_gram, top_n, fields)
        print(f"Query: '{query}' -> Extracted Dates: {response.get('extracted_dates', [])}")
        with open(f"query_data/query_{idx}_n_{n_gram}_top_{top_n}.json", "w") as f:
            json.dump(response, f, indent=2)
