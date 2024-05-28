import asyncio
import nest_asyncio
import json
import os
import re

from dotenv import load_dotenv
import langchain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()


INTENT_CLASSIFICATION_PROMPT = """
### TASK DESCRIPTION

**Task**: Classify the user input into the correct intent based on the provided descriptions and examples. Output only the intent label wrapped in a dictionary format.

**INTENTS**:
- "ask_date": The user is asking for the current date.
- "calendar_qa": The user inquires about events on their calendar.
- "out_of_scope": The query does not pertain to asking for the date or inquiring about calendar events.

**Expected Output**:
- If the user input is about asking for the date, output {{'intent': 'ask_date'}}.
- If the user input is about querying calendar events, output {{'intent': 'calendar_qa'}}.
- If the user input does not fit the categories above, output {{'intent': 'out_of_scope'}}.

### Examples

- **Input**: "What is today's date?"
  **Output**: {{'intent': 'ask_date'}}
- **Input**: "What day is it today?"
  **Output**: {{'intent': 'ask_date'}}
- **Input**: "Can you tell me what today is?"
  **Output**: {{'intent': 'ask_date'}}
- **Input**: "What do I have going on today?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "When is my next class?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Where am I dining this weekend?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What is my schedule like on June 25th?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What is happening today?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What is going on this weekend?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What is going on next week?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What did I do last weekend?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What meetings did I have the past week?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Recommend a good movie."
  **Output**: {{'intent': 'out_of_scope'}}
- **Input**: "How do you cook a steak?"
  **Output**: {{'intent': 'out_of_scope'}}
- **Input**: "Tell me a joke."
  **Output**: {{'intent': 'out_of_scope'}}
- **Input**: "What about tomorrow?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What about next week?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "And yesterday?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Where am I having lunch?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Where is my next meeting?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Where is X happening?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Where is [EVENT]?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "What is the location of [EVENT]?"
  **Output**: {{'intent': 'calendar_qa'}}
- **Input**: "Where is my next class?"
  **Output**: {{'intent': 'calendar_qa'}}

{format_instructions}

**Input**: "{query}"
**Output**:
"""


class Intent(BaseModel):
    intent: Literal["ask_date", "calendar_qa", "out_of_scope"] = Field(
        description="Classifies the user's query into 'ask_date' for queries asking about the current date, 'calendar_qa' for queries inquiring about calendar events, or 'out_of_scope' for queries that do not fit the other categories."
    )

# class Intent(BaseModel):
#     intent: Literal["ask_date", "calendar_qa", "out_of_scope"] = Field(
#         description=(
#             "Classifies the user's query into specific categories: "
#             "'ask_date' for queries asking about the current date, "
#             "'calendar_qa' for queries inquiring about calendar events, "
#             "or 'out_of_scope' for queries that do not fit the other categories."
#         )
#     )

# parser = StringOutputParser()
# parser = JsonOutputParser(pydantic_object=Intent)
intent_parser = PydanticOutputParser(pydantic_object=Intent)


def classify_intent(
    query: str,
    llm: ChatGoogleGenerativeAI,
    parser: PydanticOutputParser | JsonOutputParser = intent_parser,
    verbose: bool = False,
):

    prompt = PromptTemplate(
        template=INTENT_CLASSIFICATION_PROMPT,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # prompt = PromptTemplate(
    #     template=INTENT_CLASSIFICATION_PROMPT,
    #     input_variables=["query"],
    # ).partial(
    #     format_instructions=parser.get_format_instructions(),
    #     pattern=re.compile(r"\`\`\`\n\`\`\`"),
    # )

    chain = prompt | llm | parser

    response = chain.invoke({"query": query})

    if verbose:
        # print(
        #     f"Query: '{query}' \n -> Classified Intent: {response.get('intent', 'No intent detected')}"
        # )
        print(
            f"Query: '{query}' \n -> Classified Intent: {response.intent}"
        )

    return response


if __name__ == "__main__":

    gemini_llm = ChatGoogleGenerativeAI(
        api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-1.5-pro-latest"
    )
    # intent_parser = JsonOutputParser(pydantic_object=Intent)
    intent_parser = PydanticOutputParser(pydantic_object=Intent)

    test_queries = [
        ("What's today's date?", "ask_date"),
        ("What day is it today?", "ask_date"),
        ("Can you tell me what today is?", "ask_date"),
        ("What do I have going on today?", "calendar_qa"),
        ("When is my next class?", "calendar_qa"),
        ("Where is my Conversational AI class?", "calendar_qa"),
        ("What is my schedule like on June 25th?", "calendar_qa"),
        ("What is happening today?", "calendar_qa"),
        ("What is going on this weekend?", "calendar_qa"),
        ("What is going on next week?", "calendar_qa"),
        ("Do I have any meetings scheduled for tomorrow?", "calendar_qa"),
        ("Can you show me my agenda for the next week?", "calendar_qa"),
        ("What is the current day of the week?", "ask_date"),
        ("When is my doctor's appointment?", "calendar_qa"),
        ("Tell me what's on my calendar for December 25th.", "calendar_qa"),
        ("Is there anything planned for this Friday evening?", "calendar_qa"),
        ("How many weeks until New Year?", "out_of_scope"),
        ("Where is the location of my next meeting?", "calendar_qa"),
        ("What day of the week is Valentine's Day on next year?", "out_of_scope"),
        ("Are there any holidays coming up in next week?", "calendar_qa"),
        ("Show me the events for the last weekend", "calendar_qa"),
        ("When does daylight saving time begin?", "calendar_qa"),
        ("What appointments do I have next Monday?", "calendar_qa"),
        ("What is the date of the next full moon?", "out_of_scope"),
        ("Can you find my workout schedule?", "calendar_qa"),
        ("How old are you?", "out_of_scope"),
        ("What ingredients are in a Margarita?", "out_of_scope"),
        ("I need a recipe for a chocolate cake.", "out_of_scope"),
        ("When was the War of 1812?", "out_of_scope"),
        ("What's the date today?", "ask_date"),
        ("Do I have any appointments this afternoon?", "calendar_qa"),
        ("Can you check if I have plans next Saturday?", "calendar_qa"),
        ("Is today a holiday?", "ask_date"),
        ("What time is my flight tomorrow?", "calendar_qa"),
        ("When is my yoga class scheduled?", "calendar_qa"),
        ("Do I have any events on my birthday?", "calendar_qa"),
        ("What are the dates for the school holidays this year?", "calendar_qa"),
        ("What's happening on the first Monday of next month?", "calendar_qa"),
        ("Who am I meeting with on Wednesday?", "calendar_qa"),
        ("Is there a board meeting next week?", "calendar_qa"),
        ("Can you show me the schedule for next month?", "calendar_qa"),
        ("What events do I have this weekend?", "calendar_qa"),
        ("What’s the weather like today?", "out_of_scope"),
        ("Can you book tickets for the movie tonight?", "out_of_scope"),
        ("Where is the nearest movie theatre?", "out_of_scope"),
        ("Give me directions to the nearest coffee shop.", "out_of_scope"),
        ("Can you play some music?", "out_of_scope"),
        ("I need help with my homework.", "out_of_scope"),
        ("What are the symptoms of the flu?", "out_of_scope"),
    ]
    verbose = True

    for idx, query in enumerate(test_queries):
        response = classify_intent(query[0], gemini_llm, intent_parser, verbose)
        # response["ground_truth"] = query[1]
        # response["query"] = query[0]
        # Save response to JSON file
        query_data = {
            "query": query[0],
            "groundtruth" : query[1],
            "intent" : response.intent,
        }
        with open(f"query_data/intent_classification_{idx}.json", "w") as f:
            json.dump(query_data, f, indent=2)

