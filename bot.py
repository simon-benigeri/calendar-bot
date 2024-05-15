import asyncio
import nest_asyncio
import json
import os
import argparse
from dotenv import load_dotenv
from datetime import date
import re
from collections import Counter

import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# CALENDAR_QA_PROMPT = """\
# Today's date is {date}. If you are asked about today's date, you must respond with the date you have just been provided.

# Answer any of the user's questions about their calendar below.

# Calendar:
# {calendar}

# """


# INTENT_PROMPT = """\
# Classify the user's query into one of the following intent categories:
# {intents}

# For example:
# User: What day is it today?
# AI: ask_date

# User: When is my Korean class?
# AI: calendar_qa

# """

INTENT_PROMPT = """
    ### Prompt for Instruct Model

    **Task**: Classify the user input into the correct intent based on the provided descriptions and examples. Output only the intent label.

    **INTENTS**:
    - `ask_date`: The user is asking for the current date.
      - Examples: "What is today's date?", "What day is it today?"
    - `calendar_qa`: The user inquires about events on their calendar.
      - Examples: "What do I have going on today?", "When is {{EVENT}}?", "What days do I have {{EVENT}}?", "What time is {{EVENT}}", "When is my next class?", "Where is my Conversational AI class?"

    **Input**: "{question}"

    **Expected Output**:
    - If the user input is about asking for the date, output `ask_date`.
    - If the user input is about querying calendar events, output `calendar_qa`.

    ### Example

    **Input**: "Can you tell me what today is?"
    **Output**: `ask_date`
    """

# CALENDAR_QA_PROMPT = """\
# ### Calendar Question Answering Task

# **Today's Date**: {date}
# - When asked about today's date, always respond with the above date.

# **Task**: Answer the user's questions based on the provided calendar information. Use the details from the calendar to give specific, accurate answers about events and schedules.

# **Instructions**:
# 1. If asked for the date, respond with today's date given above.
# 2. If asked about specific events, refer to the calendar entries to provide the date, time, and details of the event.
# 3. If there is no information about a requested event, respond that no details are available.

# **Calendar**:
# {calendar}

# **Examples**:
# - Question: "What do I have going on today?"
#   Answer: "You have a meeting scheduled at 10 AM and a doctor's appointment at 3 PM."
# - Question: "When is my next team meeting?"
#   Answer: "Your next team meeting is on [date] at [time]."

# Please use the information provided to accurately respond to the user's inquiries about their calendar.
# """

CALENDAR_QA_PROMPT = """\
    ### Calendar Question Answering Task

    **Today's Date**: {date}
    - Always respond with the provided date when asked about today's date.

    **Task**: Directly answer the user's questions using the calendar information provided as JSON. Do not request additional information unless the query is ambiguous or incomplete based on the available calendar data.

    **Instructions**:
    1. Use today's date from above when asked for the date.
    2. For questions about specific events, refer directly to the calendar entries to provide accurate dates, times, and details.

    **User Calendar**:
    {calendar}

    Please ensure your responses utilize the JSON calendar provided to accurately answer inquiries. Do not seek additional personal details unless the calendar data does not cover the user's question.
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
    async for chunk in chain.astream(input):
        if verbose:
            print(chunk, end="", flush=True)
        response += chunk
    return response


async def get_intent_response(chain, input):
    response = ""
    async for chunk in chain.astream(input):
        # print(chunk, end="", flush=True)
        response += chunk
    return response


async def main(calendar, small_llm, gemini_llm):
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

        print("\n INTENT: {intent}\n")

        if intent == "ask_date":
            response = f"Today's date is {formatted_date}."
        elif intent == "calendar_qa":
            PROMPT_TEMPLATE = CALENDAR_QA_PROMPT
            # print(f"rephrased: {question}")
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
                    "calendar": json.dumps(calendar, indent=2),
                    "chat_history": chat_history,
                    "question": question,
                },
            )

        chat_history.extend(
            [HumanMessage(content=question), AIMessage(content=response)]
        )
        print(f"Response: {response}")


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

    args = parser.parse_args()
    calendar = json.load(open("my_calendar_data.json"))

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
    asyncio.run(main(calendar[:10], small_llm, gemini_llm))
