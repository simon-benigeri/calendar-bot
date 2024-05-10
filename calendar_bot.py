import asyncio
import nest_asyncio
import json
import os
from dotenv import load_dotenv
from datetime import date

import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
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


PROMPT_TEMPLATE = """\
Today's date is {date}. 
If you are asked about today's date, you must respond with the date you have just been provided.

For example:
User: What is today's date?
AI: Today's date is {date}. 

Answer any of the user's questions about their calendar below.

Calendar:
{calendar}

"""

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

        # print(f"rephrased: {question}")
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PROMPT_TEMPLATE),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        chain = prompt | llm | StrOutputParser()

        today = date.today()
        formatted_date = today.strftime("%B %d, %Y")

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


if __name__ == "__main__":
    calendar = load_calendar("my_calendar_data.json")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest")
    nest_asyncio.apply()
    # submit full calendar by removing the [0]. only passing the first event here
    asyncio.run(main(calendar[0]))
