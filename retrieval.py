import json
from datetime import date, datetime, timedelta
import dateparser

from rank_bm25 import BM25Okapi
import nltk
from nltk.corpus import stopwords
from nltk.util import ngrams

nltk.download('punkt')
nltk.download('stopwords')


# def extract_date(query):
#     # Attempt to parse a date from the query
#     date = dateparser.parse(query, settings={'PREFER_DATES_FROM': 'future'})
#     if date:
#         return date.strftime("%Y-%m-%d")
#     else:
#         # Default to today's date if no date is found
#         # return datetime.now().strftime("%Y-%m-%d")
#         return None

def get_next_weekday(start_date, weekday):
    """
    Given a start date and a weekday, calculate the date of the next occurrence of that weekday.
    """
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return start_date + timedelta(days_ahead)

def extract_date(query, date_format="%A %B %d"):
    today = datetime.now()
    
    # Lowercase the query to handle case insensitivity
    query_lower = query.lower()

    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(weekdays):
        if day in query_lower:
            # Check if 'next' is explicitly mentioned to avoid confusion
            if 'next' in query_lower:
                next_day_date = get_next_weekday(today, i)
                return [next_day_date.strftime(date_format)]
            else:
                # Return today if today matches the day and it's not specified as 'next'
                if today.weekday() == i:
                    return [today.strftime(date_format)]
                else:
                    next_day_date = get_next_weekday(today, i)
                    return [next_day_date.strftime(date_format)]

    if 'today' in query_lower:
        return [today.strftime(date_format)]
    elif 'tomorrow' in query_lower:
        tomorrow = today + timedelta(days=1)
        return [tomorrow.strftime(date_format)]
    elif 'this weekend' in query_lower:
        start_weekend = today + timedelta((5 - today.weekday()) % 7)  # Calculate next Saturday
        end_weekend = start_weekend + timedelta(days=1)  # Next Sunday
        return [start_weekend.strftime(date_format), end_weekend.strftime(date_format)]
    elif 'next week' in query_lower:
        start_next_week = today + timedelta((7 - today.weekday()) % 7)
        week_dates = [start_next_week + timedelta(days=i) for i in range(7)]
        return [date.strftime(date_format) for date in week_dates]

    # Use dateparser for other expressions
    date = dateparser.parse(query, settings={'PREFER_DATES_FROM': 'future'})
    if date:
        return [date.strftime(date_format)]
    else:
        return []
    

def append_dates_to_query(query):
    # Extract dates from the query
    dates = extract_date(query)
    
    # Append extracted dates to the query, if any
    if dates:
        updated_query = f"{query} on {' and '.join(dates)}"
    else:
        updated_query = query

    return updated_query
    

# def bm25_retrieve_from_json(docs, query, fields, n_gram=1, top_n=5):
#     # Combine specified fields and tokenize, using n-grams up to length of the longest phrase
#     tokenized_docs = [tokenize("\n".join(doc[field] for field in fields if field in doc), n=n_gram) for doc in docs]
#     bm25 = BM25Okapi(tokenized_docs)

#     # Tokenize query
#     tokenized_query = tokenize(query)

#     # Get scores and retrieve top N documents
#     scores = bm25.get_scores(tokenized_query)

#     # Update documents with their scores
#     for score, doc in zip(scores, docs):
#         doc['bm25_score'] = score

#     top_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
#     return [docs[i] for i in top_indexes]

def bm25_retrieve_from_json(docs, query, fields, n_gram=1, top_n=5):
    # Extract dates and append to the query for more context
    updated_query = append_dates_to_query(query)
    extracted_date = extract_date(query)
    
    # Tokenization of documents
    tokenized_docs = [tokenize("\n".join(str(doc[field]) for field in fields if field in doc and field not in ['date', 'start']), n=n_gram) for doc in docs]
    bm25 = BM25Okapi(tokenized_docs)

    # Tokenization of the query
    tokenized_query = tokenize(updated_query)

    # Compute BM25 scores
    bm25_scores = bm25.get_scores(tokenized_query)

    # Calculate scores and add to docs
    for doc, bm25_score in zip(docs, bm25_scores):
        date_score = 1 if extracted_date and extracted_date in doc.get('date', '') else 0
        doc['date_score'] = date_score
        doc['bm25_score'] = bm25_score

    # First, retrieve all documents with date_score greater than 1
    retrieved_docs = [doc for doc in docs if doc['date_score'] > 0]

    # If there are not enough documents retrieved, fill up the rest with those having the highest BM25 scores
    if len(retrieved_docs) < top_n:
        remaining_docs_needed = top_n - len(retrieved_docs)
        remaining_docs = [doc for doc in sorted(docs, key=lambda x: x['bm25_score'], reverse=True) if doc not in retrieved_docs][:remaining_docs_needed]
        retrieved_docs.extend(remaining_docs)
    
    # Sort documents by dateTime within the 'start' field
    retrieved_docs.sort(key=lambda doc: datetime.strptime(doc['start']['dateTime'], '%Y-%m-%dT%H:%M:%S%z'))

    # Drop the 'start' field from each document
    for doc in retrieved_docs:
        doc.pop('start', None)  # Safely remove the 'start' field without causing an error if it's missing

    return retrieved_docs



def tokenize(text, n=1):
    # Tokenize the text
    words = nltk.word_tokenize(text.lower())
    
    # Filter out stopwords
    filtered_words = [word for word in words if word not in stopwords.words('english')]
    
    # Calculate n if not provided, assuming the max length for a phrase like "Saturday May 18"
    if n is None:
        n = len(filtered_words)
    
    # Generate unigrams and up to n-grams
    all_ngrams = []
    for i in range(1, n + 1):
        generated_ngrams = ngrams(filtered_words, i)
        all_ngrams.extend([' '.join(gram) for gram in generated_ngrams])
    
    return all_ngrams


if __name__=="__main__":

    calendar = json.load(open("my_calendar_data_filtered.json"))

    # # Example cases
    queries = ["What's happening Wednesday?", "What's happening next Monday?", "Remind me every Tuesday", "Schedule for this weekend", "What's happening today?", "Meet me tomorrow", "Let's plan for this weekend", "Schedule for next week"]

    docs = calendar

    fields = ["id", "date", "location", "summary", "description"]
    n_gram = 3
    top_n = 3
    for idx, query in enumerate(queries):
        extracted_date = extract_date(query)
        print(f"Query: '{query}' -> Extracted Date: {extracted_date}")
        enriched_query = append_dates_to_query(query)
        print(f"Enriched Query: {enriched_query}")
        top_n = max(top_n, len(extracted_date))
        relevant_docs = bm25_retrieve_from_json(docs, enriched_query, fields, n_gram=n_gram, top_n=top_n)
        response = {
            "query": query,
            "n_gram": n_gram,
            "top_n": top_n,
            "fields": fields,
            "extracted_date": extracted_date,
            "relevant_docs": relevant_docs,
            
        }
        with open(f'query_{idx}_n_{n_gram}_top_{top_n}.json', 'w') as f:
            json.dump(response, f, indent=2)


    # query = "What is going on today?"

    # print(f"query: {query}")
    # dates = extract_date(query)
    # print(f"dates: {dates}")
    # enriched_query = append_dates_to_query(query)
    # # print(f"enriched_query: {enriched_query}")

    # # print(ass)

    # docs = calendar

    # fields = ["date", "summary", "location"]

    # # # fields = 
    # relevant_docs = bm25_retrieve_from_json(docs, enriched_query, fields, n_gram=1, top_n=1)

    # print(relevant_docs)

    # queries = [
    #     "what is happening today?",
    #     "what is my schedule like tomorrow?",
    #     "What is happening this weekend?",
    # ]
    # for query in queries:
    #     query_date = extract_date(query)
    #     print(query_date)