import asyncio
import nest_asyncio
import json
import os
import argparse
from datetime import date, datetime
import re
from collections import Counter
import dateparser

from dotenv import load_dotenv

import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_core.messages import HumanMessage, AIMessage

# from retrieval import retrieve_docs
from sbert_retrieval import retrieve_docs, build_annoy_index

load_dotenv()


INTENT_PROMPT = """
    ### Prompt for Instruct Model

    **Task**: Classify the user input into the correct intent based on the provided descriptions and examples. Output only the intent label.

    **INTENTS**:
    - `ask_date`: The user is asking for the current date.
      - Examples: "What is today's date?", "What day is it today?"
    - `calendar_qa`: The user inquires about events on their calendar.
      - Examples: "What do I have going on today?", "When is {{EVENT}}?", "What days do I have {{EVENT}}?", "What time is {{EVENT}}", "When is my next class?", "Where is my Conversational AI class?", "What is my schedule like on {{DATE}}?", "What is happening today?", "What is going on this weekend?", "What is going on next week?"

    **Input**: "{question}"

    **Expected Output**:
    - If the user input is about asking for the date, output `ask_date`.
    - If the user input is about querying calendar events, output `calendar_qa`.

    ### Example

    
    **Input**: "Can you tell me what today is?"
    **Output**: `ask_date`
    """
# INTENT_PROMPT = prompt = """
# ### TASK DESCRIPTION

# **Task**: Classify the user input into the correct intent based on the provided descriptions and examples. Output only the intent label.

# **INTENTS**:
# - `ask_date`: The user is asking for the current date.
# - `calendar_qa`: The user inquires about events on their calendar.

# **Expected Output**:
# - If the user input is about asking for the date, output `ask_date`.
# - If the user input is about querying calendar events, output `calendar_qa`.

# ### Example

# - **Input**: "What is today's date?"
#   **Output**: `ask_date`
# - **Input**: "What day is it today?"
#   **Output**: `ask_date`
# - **Input**: "Can you tell me what today is?"
#   **Output**: `ask_date`
# - **Input**: "What do I have going on today?"
#   **Output**: `calendar_qa`
# - **Input**: "When is my next class?"
#   **Output**: `calendar_qa`
# - **Input**: "Where is my Conversational AI class?"
#   **Output**: `calendar_qa`
# - **Input**: "What is my schedule like on June 25th?"
#   **Output**: `calendar_qa`
# - **Input**: "What is happening today?"
#   **Output**: `calendar_qa`
# - **Input**: "What is going on this weekend?"
#   **Output**: `calendar_qa`
# - **Input**: "What is going on next week?"
#   **Output**: `calendar_qa`

  
# **Input**: "{question}"
# **Output**:
# """

CALENDAR_QA_PROMPT = """\
    ### Calendar Question Answering Task

    **Today's Date**: {date}
    - Always respond with the provided date when asked about today's date.

    **Task**: Directly answer the user's questions using the provided calendar information. Do not request additional information unless the query is ambiguous or incomplete based on the available calendar data.

    **Instructions**:
    1. Use today's date from above when asked for the date.
    2. For questions about specific events, refer directly to the calendar entries to provide accurate dates, times, and details.
    3. If the user's question pertains to an event not listed or is unclear, clarify what additional information is needed to answer effectively, while still attempting to provide as much relevant information as possible based on the available data.

    **Provided Calendar**:
    {calendar}

    **Example Responses**:
    - Question: "What do I have going on today?"
    Answer: "Today, you have a doctor's appointment at 3 PM and a team meeting at 10 AM."
    - Question: "When is my next team meeting?"
    Answer: "Your next team meeting is scheduled for [insert date here] at [insert time here]."
    - Question: "Is there anything on my calendar about the project deadline?"
    Answer: "Your project deadline is noted on [insert date here]."

    Please ensure your responses utilize the calendar provided to accurately answer inquiries. Do not seek additional personal details unless the calendar data does not cover the user's question.
    """


def extract_most_frequent_intent(response):
    # Define the patterns to search for explicit intent labels
    patterns = ["ask_date", "calendar_qa"]

    # Find all occurrences of the patterns in the response
    matches = re.findall(
        r"\b(?:" + "|".join(patterns) + r")\b", response, re.IGNORECASE
    )

    # Count occurrences and determine the most frequent intent
    if matches:
        most_common = Counter(matches).most_common(1)[0][0]
    else:
        most_common = "No intent found"

    return most_common


async def get_response(chain, input, verbose=True):
    response = ""
    # Print the prefix once before the chunks start arriving
    if verbose:
        print("Response: ", end="", flush=True)

    # Print each chunk as it arrives
    async for chunk in chain.astream(input):
        if verbose:
            print(chunk, end="", flush=True)
        response += chunk

    return response


async def main(calendar, annoy_index, small_llm, gemini_llm, top_n, verbose=False):
    chat_history = []

    while True:
        question = input("Please enter your question or type 'exit' to quit: ")
        if question.lower() == "exit":
            print("Exiting the program.")
            break

        today = date.today()
        formatted_date = today.strftime("%B %d, %Y")

        intent_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", INTENT_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        intent_chain = intent_prompt | small_llm | StrOutputParser()
        intent_response = await get_response(
            intent_chain,
            input={
                "chat_history": chat_history,
                "question": question,
            },
            verbose=False,
        )

        intent = extract_most_frequent_intent(intent_response)

        if verbose:
            print(f"INTENT: {intent}")

        if intent == "ask_date":
            response = f"Today's date is {formatted_date}."
            print(f"Response: {response}")
        # elif intent == "calendar_qa":
        else:

            retriever_response = retrieve_docs(
                query=question, docs=calendar, index=annoy_index, top_n=top_n
            )

            relevant_docs = retriever_response.get("relevant_docs", {})

            if verbose:
                print(f"N DOCUMENTS RETRIEVED: {len(relevant_docs)}")
                print(
                    f"EXTRACTED DATES: {retriever_response.get('extracted_dates', [])}"
                )
                print(f"DOCUMENTS RETRIEVED: {json.dumps(relevant_docs, indent=2)}")

            PROMPT_TEMPLATE = CALENDAR_QA_PROMPT

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("human", PROMPT_TEMPLATE),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}"),
                ]
            )
            chain = prompt | gemini_llm | StrOutputParser()

            response = await get_response(
                chain,
                input={
                    "date": formatted_date,
                    "calendar": json.dumps(relevant_docs, indent=2),
                    "chat_history": chat_history,
                    "question": question,
                },
            )

        chat_history.extend(
            [HumanMessage(content=question), AIMessage(content=response)]
        )
        # print(f"Response: {response}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interact with a chat model to process calendar and date inquiries."
    )
    parser.add_argument(
        "-g",
        "--gemini",
        action="store_true",
        help="Use Gemini API, if not, use Ollama model phi-3.",
    )

    parser.add_argument(
        "-n",
        "--top_n",
        default=3,
        help="Top n documents to retrieve.",
    )

    parser.add_argument(
        "-f",
        "--fields",
        default=["location", "summary", "description"],
        help="Text fields in calendar for annoy index.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detected intent, n docs retrieved, and dates extracted",
    )

    args = parser.parse_args()
    calendar = json.load(open("my_calendar_data_filtered.json"))
    for i, event in enumerate(calendar):
        event["index_id"] = i

    print("Building index of calendar documents.")
    annoy_index = build_annoy_index(calendar, args.fields)

    if args.gemini:
        gemini_llm = ChatGoogleGenerativeAI(
            api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-pro-latest"
        )
        small_llm = ChatOllama(model="mistral:instruct")
        print("Using Gemini API and Ollama model mistral:instruct.")
    else:
        # llm = ChatOllama(model="phi3")
        # print("Using Ollama model phi-3.")
        small_llm = ChatOllama(model="mistral:instruct")
        gemini_llm = small_llm
        print("Using Ollama model mistral:instruct.")


    nest_asyncio.apply()
    asyncio.run(
        main(calendar, annoy_index, small_llm, gemini_llm, args.top_n, args.verbose)
    )
