import asyncio
import nest_asyncio
import json
import os
import argparse
from dotenv import load_dotenv
from datetime import date

import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_core.messages import HumanMessage, AIMessage

langchain.verbose = True

# Load GOOGLE API KEY
load_dotenv()  # load all the environment variables from .env file

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.getenv(
        "GOOGLE_API_KEY"
    )  # getpass.getpass("Provide your Google API Key")


def load_calendar(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


# PROMPT_TEMPLATE = """\
# Today's date is {date}. 
# If you are asked about today's date, you must respond with the date you have just been provided.

# For example:
# User: What is today's date?
# AI: Today's date is {date}. 

# Answer any of the user's questions about their calendar below.

# Calendar:
# {calendar}

# """

# PROMPT_TEMPLATE = """\
# Today's date is {date}. 
# The phrase "today’s date" does not refer to the actual calendar date of today. 
# It refers to the fact that in this application, there is a token or variable, "today’s date."
# If you are asked about today's date, are being asked about this variable.

# For example:
# User: What is today's date?
# AI: Today's date is {date}. 

# Answer any of the user's questions about their calendar below.

# Calendar:
# {calendar}

# """

CALENDAR_QA_PROMPT = """\
Today's date is {date}. If you are asked about today's date, you must respond with the date you have just been provided.

Answer any of the user's questions about their calendar below.

Calendar:
{calendar}

"""


INTENT_PROMPT = """\
Classify the user's query into one of the following intent categories:
{intents}

For example:
User: What day is it today?
AI: ask_date

User: When is my Korean class?
AI: calendar_qa

"""

INTENTS = {
    "ask_date": {
        "description": "User asks for the date",
        "examples": [
            "What is today's date?",
            "What day is it today?",
        ]
    },
    "calendar_qa": {
        "description": "User asks about their calendar",
        "examples": [
            "What do I have going on today?",
            "When is {EVENT}?",
            "What days do I have {EVENT}?",
            "What time is {EVENT}"
        ]
    }
}


async def get_response(chain, input):
    # print(f"Sending the following prompt to the model: {input}")
    response = ""
    async for chunk in chain.astream(input):
        print(chunk, end="", flush=True)  # This prints each chunk as it is received.
        response += chunk  # Append each chunk to the response variable.
    return response  # Return the complete response after all chunks are received.


async def main(calendar):
    chat_history = []

    while True:
        question = input("Please enter your question or type 'exit' to quit: ")
        if question.lower() == "exit":
            print("Exiting the program.")
            break

        print(f"question: {question}")

        today = date.today()
        formatted_date = today.strftime("%B %d, %Y")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CALENDAR_QA_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        chain = prompt | llm | StrOutputParser()
        
        response = await get_response(
            chain,
            input={
                "date": formatted_date,
                "calendar": json.dumps(calendar, indent=2),
                "chat_history": chat_history,
                "question": question,
            },
        )
        # response = chain.invoke(
        #     {"date": formatted_date, "calendar": json.dumps(calendar[0], indent=2), "chat_history": chat_history, "question": question}
        # )

        chat_history.extend(
            [
                HumanMessage(content=question),
                AIMessage(content=response),
            ]
        )

        # print(f"response: {response}")


# Create the parser
parser = argparse.ArgumentParser(
    description="This script allows the user to choose between using the Gemini API or the Ollama model phi-3."
)

# Add the '--gemini' boolean flag
parser.add_argument(
    "-g",
    "--gemini",
    action="store_true",
    default=False,
    help="Use Gemini API, if not, use Ollama model phi-3.",
)


if __name__ == "__main__":
    # Parse the arguments
    args = parser.parse_args()
    calendar = load_calendar("my_calendar_data.json")
    if args.gemini:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest")
        print("Using Gemini API.")
    else:
        llm = ChatOllama(model="phi3")
        print("Using Ollama model phi-3.")
    nest_asyncio.apply()
    # submit full calendar by removing the [0]. only passing the first event here
    asyncio.run(main(calendar[0]))
