import asyncio
import nest_asyncio
import json
import os
import re
from datetime import date

from dotenv import load_dotenv

import langchain
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List

load_dotenv()

DATE_EXTRACTION_PROMPT = """
### Task Instructions

Given today's date of {date}, you are provided with a single date-related query. Your task is to analyze the query and determine the specific dates it refers to. Follow these guidelines to complete the task:

1. **Identify the Date(s)**: Determine the exact date or date range the query refers to based on its context.
2. **Handle Recurring Dates**: If the query refers to a recurring event (e.g., "Remind me every Tuesday"), calculate and return the four nearest upcoming dates starting from today.
3. **Format the Output**: Return the results as a dictionary with a key 'extracted_dates' that maps to a list of strings, where each string represents a date formatted in the "Month DD, YYYY" format. For date ranges, the list should include strings representing each day covered.
4. **No Date References**: If the query does not reference any specific dates or date ranges, return a dictionary with the key 'extracted_dates' pointing to an empty list.

### Example Execution

Suppose you are provided with the query: "Schedule for this weekend". 

**Example Task Execution**:
query = "Schedule for this weekend", Date = "Friday, May 24, 2024"
output: {{
    "extracted_dates": ["May 25, 2024", "May 26, 2024"]
}}

query = "Check for non-date event", Date = "Friday, May 24, 2024"
output: {{
    "extracted_dates": []
}}

query = "When do I have meetings this week?", Date = "Monday, May 27, 2024"
output: {{
    "extracted_dates": ["May 27, 2024", "May 28, 2024", "May 29, 2024", "May 30, 2024", "May 31, 2024", "June 1, 2024", "June 2, 2024"]
}}

query = "What is happening tomorrow?, Date = "Tuesday, May 28, 2024"
output: {{
    "extracted_dates": ["May 29, 2024"]
}}

query = "What is my schedule next Tuesday?, Date = "Monday, May 27, 2024" 
output: {{
    "extracted_dates": ["May 28, 2024"]
}}

Ensure each date is accurately calculated considering today’s date, ensuring that you address the query with precision and contextual awareness of the day of the week and calendar date. 

{format_instructions}

query = {query}
"""


class Dates(BaseModel):
    extracted_dates: List[str] = Field(
        description="List of extracted dates in 'Month DD, YYYY' format"
    )


# date_parser = JsonOutputParser(pydantic_object=Dates)
date_parser = PydanticOutputParser(pydantic_object=Dates)


def extract_dates(
    query,
    llm,
    formatted_date,
    parser: JsonOutputParser | PydanticOutputParser = date_parser,
    verbose: str = False,
):

    try:
        prompt = PromptTemplate(
            template=DATE_EXTRACTION_PROMPT,
            input_variables=["date", "query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | llm | parser

        response = chain.invoke({"date": formatted_date, "query": query})
    # response["query"] = query
    # response["today"] = formatted_date
    except:

        # if we don't get a response, try again with this
        prompt = PromptTemplate(
            template=PromptTemplate,
            input_variables=["date", "query"],
        ).partial(
            format_instructions=parser.get_format_instructions(),
            pattern=re.compile(r"\`\`\`\n\`\`\`"),
        )
    if verbose:
        # print(
        #     f"Current Date: {formatted_date} \n -> Extracted Dates: {response.get('extracted_dates', [])}"
        # )
        print(
            f"Query: {query} \n  Current Date: {formatted_date} \n    -> Extracted Dates: {response.extracted_dates}"
        )

    return response


if __name__ == "__main__":
    verbose = True

    today = date.today()
    formatted_date = today.strftime("%A, %B %d, %Y")

    gemini_llm = ChatGoogleGenerativeAI(
        api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-pro-latest"
    )
    # date_parser = JsonOutputParser(pydantic_object=Dates)
    date_parser = PydanticOutputParser(pydantic_object=Dates)

    queries = [
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

    for idx, query in enumerate(queries):
        response = extract_dates(
            query, gemini_llm, formatted_date, date_parser, verbose
        )

        # print(
        #     f"Query: '{query}' \n Current Date: {formatted_date} \n -> Extracted Dates: {response.get('extracted_dates', [])}"
        # )
        # print(
        #     f"Current Date: {formatted_date} \n -> Extracted Dates: {response.extracted_dates}"
        # )

        query_data = {
            "query": query,
            "today": formatted_date,
            "extracted_dates": response.extracted_dates,
        }

        with open(f"query_data/gemini_date_retrieval_{idx}.json", "w") as f:
            json.dump(query_data, f, indent=2)
