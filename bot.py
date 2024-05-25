import asyncio
import nest_asyncio
import json
import os
import argparse
from datetime import date
from typing import List, Dict
import time


import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables.base import RunnableSequence
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from annoy import AnnoyIndex

from retrieval import retrieve_docs, build_annoy_index
from date_extraction import extract_dates, date_parser, Dates
from intent_classifier import classify_intent, intent_parser, Intent
from dotenv import load_dotenv

load_dotenv()


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


async def get_intent(
    query: str,
    llm: ChatGoogleGenerativeAI,
    parser: PydanticOutputParser | JsonOutputParser = intent_parser,
) -> Intent:
    """Async function to classify intent."""
    return classify_intent(query=query, llm=llm, parser=parser)


async def get_dates(
    query: str,
    llm: ChatGoogleGenerativeAI,
    formatted_date: str,
    parser: PydanticOutputParser | JsonOutputParser = date_parser,
) -> Dates:
    """Async function to extract dates from query."""
    return extract_dates(
        query=query, llm=llm, formatted_date=formatted_date, parser=parser
    )


# async def get_response(
#     chain: RunnableSequence, input: Dict, verbose: int = 0
# ) -> str:
#     """Async function collect Gemini response and stream the output (looks nicer)."""
#     response = ""
#     # Print the prefix once before the chunks start arriving
#     if verbose > 0:
#         print("Response: ", end="", flush=True)

#     # Print each chunk as it arrives
#     async for chunk in chain.astream(input):
#         if verbose > 0:
#             print(chunk, end="", flush=True)
#         response += chunk

#     return response


async def get_response(chain: RunnableSequence, input: Dict) -> str:
    """Async function collect Gemini response and prints each chunk as it arrives (looks nicer)."""
    print("Response: ", end="", flush=True)
    response = ""
    async for chunk in chain.astream(input):
        print(chunk, end="", flush=True)
        response += chunk
    return response


async def main(
    calendar: List[Dict],
    annoy_index: AnnoyIndex,
    llm: ChatGoogleGenerativeAI | ChatOllama,
    top_n: int = 3,
    verbose: int = 1,
    use_async=False,
):
    """Main function to run the chatbot.
    1. read user input query
    2. classify intent
    3. if intent is calendar_qa, extract dates, retrieve documents, and chat w/ Gemini.
    """
    chat_history = []

    while True:
        question = input("Please enter your question or type 'exit' to quit: ")
        if question.lower() == "exit":
            print("Exiting the program.")
            break

        today = date.today()
        formatted_date = today.strftime("%B %d, %Y")

        start_time = time.time()  # Start timing
        if use_async:
            intent = await get_intent(query=question, llm=llm, parser=intent_parser)
        else:
            intent = classify_intent(query=question, llm=llm, parser=intent_parser)

        if verbose > 1:
            print(f"Intent retrieval time: {time.time() - start_time:.2f} seconds")

        if verbose > 0:
            print(f"INTENT: {intent.intent}")

        if intent.intent == "ask_date":
            response = f"Today's date is {formatted_date}."
            print(f"Response: {response}")
        elif intent.intent == "out_of_scope":
            response = f"I can only answer questions about today's date or your personal calendar."
            print(f"Response: {response}")
        # elif intent == "calendar_qa":
        else:
            start_time = time.time()  # Start timing

            if use_async:
                dates = await get_dates(
                    query=question,
                    llm=llm,
                    formatted_date=formatted_date,
                    parser=date_parser,
                )
            else:
                dates = extract_dates(
                    query=question,
                    llm=llm,
                    formatted_date=formatted_date,
                    parser=date_parser,
                )
            if verbose > 1:
                print(f"Date extraction time: {time.time() - start_time:.2f} seconds")

            start_time = time.time()  # Start timing
            # TODO: check if this didnt break with pydantic
            retriever_response = retrieve_docs(
                query=question,
                extracted_dates=dates.extracted_dates,
                docs=calendar,
                index=annoy_index,
                top_n=top_n,
            )
            if verbose > 1:
                print(
                    f"Document retrieval time: {time.time() - start_time:.2f} seconds"
                )

            relevant_docs = retriever_response.get("relevant_docs", {})

            if verbose > 0:
                print(f"N DOCUMENTS RETRIEVED: {len(relevant_docs)}")
                print(f"EXTRACTED DATES: {dates.extracted_dates}")
            
            if verbose > 2:
                print(f"DOCUMENTS RETRIEVED: {json.dumps(relevant_docs, indent=2)}")

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("human", CALENDAR_QA_PROMPT),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}"),
                ]
            )
            chain = prompt | llm | StrOutputParser()

            start_time = time.time()  # Start timing
            response = await get_response(
                chain,
                input={
                    "date": formatted_date,
                    "calendar": json.dumps(relevant_docs, indent=2),
                    "chat_history": chat_history,
                    "question": question,
                },
            )
            if verbose > 1:
                print(
                    f"Response generation time: {time.time() - start_time:.2f} seconds"
                )

        chat_history.extend(
            [HumanMessage(content=question), AIMessage(content=response)]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interact with a chat model to process calendar and date inquiries."
    )
    parser.add_argument(
        "-g",
        "--gemini",
        action="store_true",
        help="Use Gemini API, if not, use Ollama model mistral:instruct.",
    )

    parser.add_argument(
        "-a",
        "--use_async",
        action="store_true",
        help="Use async for intent classification and date extraction.",
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
        choices=[0, 1, 2, 3],
        default=0,
        type=int,
        help=(
            "Control the verbosity of the output: "
            "0 -> Print only the response; "
            "1 -> Print detected intent, number of documents retrieved, and dates extracted; "
            "2 -> Additionally, print processing time; "
            "3 -> Additionally, print details of the retrieved documents."
        ),
    )

    args = parser.parse_args()
    calendar = json.load(open("my_calendar_data_filtered.json"))
    for i, event in enumerate(calendar):
        event["index_id"] = i

    print("Building index of calendar documents.")
    start_time = time.time()  # Start timing
    annoy_index = build_annoy_index(calendar, args.fields)

    if args.verbose > 1:
        print(f"Annoy index building time: {time.time() - start_time:.2f} seconds")

    if args.gemini:
        llm = ChatGoogleGenerativeAI(
            api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-pro-latest"
        )
        print("Using Gemini API.")
    else:
        llm = ChatOllama(model="mistral:instruct")
        print("Using Ollama model mistral:instruct.")

    nest_asyncio.apply()
    asyncio.run(
        main(
            calendar=calendar,
            annoy_index=annoy_index,
            llm=llm,
            top_n=args.top_n,
            verbose=args.verbose,
            use_async=args.use_async,
        )
    )
