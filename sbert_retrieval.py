import json
from datetime import datetime, timedelta
import dateparser
from typing import List, Dict
import torch
from transformers import AutoTokenizer, AutoModel
from annoy import AnnoyIndex

# Initialize tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")


def get_embeddings(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.squeeze().numpy()


def build_annoy_index(
    docs, text_fields: List[str], embedding_dim: int = 384, n_trees: int = 10
):
    index = AnnoyIndex(embedding_dim, "angular")
    for i, doc in enumerate(docs):
        doc_text = " ".join([str(doc.get(field, "")) for field in text_fields])
        embedding = get_embeddings(doc_text)
        index.add_item(doc["index_id"], embedding)
    index.build(n_trees)
    return index


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


def retrieve_with_dates(docs, query):
    extracted_dates = extract_date(query)
    for doc in docs:
        date_score = (
            1
            if any(
                extracted_date in doc.get("date", "")
                for extracted_date in extracted_dates
            )
            else 0
        )
        doc["date_score"] = date_score

    return [doc for doc in docs if doc["date_score"] > 0], extracted_dates


def retrieve_with_sbert(query, docs, index, top_n=5, exclude_ids=set()):
    query_embedding = get_embeddings(query)
    nearest_ids, scores = index.get_nns_by_vector(
        query_embedding, len(docs), include_distances=True
    )  # Query all documents

    # Assign scores to all documents immediately
    for doc_id, score in zip(nearest_ids, scores):
        docs[doc_id]["sbert_score"] = score

    # Filter out excluded documents and select the top scoring ones
    scored_docs = [docs[i] for i in nearest_ids if docs[i]["id"] not in exclude_ids]

    # Sort by SBERT score to get the best results
    scored_docs.sort(key=lambda doc: doc["sbert_score"])

    return scored_docs[:top_n]  # Return only top_n results


def retrieve_docs(query, docs, index, top_n=3):
    # Assign SBERT scores to all documents
    all_docs_scored = retrieve_with_sbert(query, docs, index, top_n=len(docs))

    # Retrieve documents based on date matching
    date_retrieved_docs, extracted_dates = retrieve_with_dates(docs, query)

    date_retrieved_doc_ids = {doc["id"] for doc in date_retrieved_docs}

    # Filter SBERT scored docs excluding the date-retrieved ones to avoid duplication
    additional_docs_needed = max(0, top_n - len(date_retrieved_docs))

    additional_sbert_docs = [
        doc for doc in all_docs_scored if doc["id"] not in date_retrieved_doc_ids
    ][:additional_docs_needed]

    # Combine date-retrieved docs with additional SBERT docs
    combined_docs = date_retrieved_docs + additional_sbert_docs

    response = {
        "query": query,
        "top_n": top_n,
        "relevant_docs": combined_docs,  # Ensure we return exactly top_n docs
        "extracted_dates": extracted_dates,
    }
    return response


if __name__ == "__main__":

    calendar = json.load(open("my_calendar_data_filtered.json"))
    for i, event in enumerate(calendar):
        event["index_id"] = i

    # fields = ["id", "date", "start", "location", "summary", "description"]
    text_fields = ["location", "summary", "description"]
    top_n = 3

    annoy_index = build_annoy_index(calendar, text_fields)

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
        "When is the match?",
        "When is the football game?",
        "When do Arsenal play",
    ]

    for idx, query in enumerate(queries):
        response = retrieve_docs(query, docs=calendar, index=annoy_index, top_n=top_n)
        print(
            f"Query: '{query}' -&gt; Relevant Docs: {len(response.get('relevant_docs', []))}"
        )
        print(
            f"Query: '{query}' -> Extracted Dates: {response.get('extracted_dates', [])}"
        )
        with open(f"query_data/sbert_query_{idx}_top_n_{top_n}.json", "w") as f:
            json.dump(response, f, indent=2)
