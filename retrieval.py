import os
from datetime import date, datetime
import json
from typing import List, Dict
import torch
from transformers import AutoTokenizer, AutoModel
from annoy import AnnoyIndex
from langchain_google_genai import ChatGoogleGenerativeAI


from dotenv import load_dotenv

from date_extraction import extract_dates

load_dotenv()

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


def format_doc_date(doc_date):
    # Attempt to parse the date string
    # The format string "%A %B %d, %Y, %I:%M%p" should be capable of parsing "DayOfWeek Month Day, Year, Time"
    # If this fails, we need to ensure the input string matches this expected format
    try:
        # Splitting the string to remove the time part before parsing
        date_part = doc_date.split(",")[0] + "," + doc_date.split(",")[1]
        # Now parse the date with correct format after the split
        parsed_date = datetime.strptime(date_part, "%A %B %d, %Y")

        # Format the date to only show "Month DD, YYYY"
        formatted_date = parsed_date.strftime("%B %d, %Y")

        return formatted_date
    except ValueError as e:
        print(f"Error parsing the date: {e}")
        return None


def retrieve_with_dates(docs, extracted_dates):
    for doc in docs:
        doc_date = format_doc_date(doc.get("date", ""))
        date_score = 1 if doc_date in extracted_dates else 0
        doc["date_score"] = date_score
    return [doc for doc in docs if doc["date_score"] > 0]


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


def retrieve_docs(query, extracted_dates, docs, index, top_n=3):
    # Assign SBERT scores to all documents
    all_docs_scored = retrieve_with_sbert(query, docs, index, top_n=len(docs))

    # Retrieve documents based on date matching
    date_retrieved_docs = retrieve_with_dates(docs, extracted_dates)

    date_retrieved_doc_ids = {doc["id"] for doc in date_retrieved_docs}

    print(len(date_retrieved_doc_ids))

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
        "What's happening tomorrow?",
        "What's happening Wednesday?",
        "What's happening next Monday?",
        "Remind me every Tuesday",
        "Schedule for this weekend",
        "What's happening today?",
        "Meet me tomorrow",
        "Let's plan for this weekend",
        "Schedule for next week",
        "What happened last Thursday?",
        "Summary of the previous week",
        "Activities from the past weekend",
        "When is the match?",
        "When is the football game?",
        "When do Arsenal play",
    ]

    today = date.today()
    formatted_date = today.strftime("%A, %B %d, %Y")

    gemini_llm = ChatGoogleGenerativeAI(
        api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-pro-latest"
    )

    verbose = True

    for idx, query in enumerate(queries):
        extracted_dates = extract_dates(
            query=query, llm=gemini_llm, formatted_date=formatted_date, verbose=verbose
        )
        response = retrieve_docs(
            query,
            docs=calendar,
            extracted_dates=extracted_dates.get("extracted_dates", []),
            index=annoy_index,
            top_n=top_n,
        )
        print(
            f"Query: '{query}' -&gt; Relevant Docs: {len(response.get('relevant_docs', []))}"
        )
        # print(
        #     f"Query: '{query}' -> Extracted Dates: {response.get('extracted_dates', [])}"
        # )
        with open(f"query_data/sbert_query_{idx}_top_n_{top_n}.json", "w") as f:
            json.dump(response, f, indent=2)
