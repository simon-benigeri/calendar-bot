from langchain.llms import GPT4ALL
from langchain.chains import SingleLLMChain
import json

# Initialize the LLM
llm = GPT4ALL(api_key="your_api_key_here")

# Create a Langchain chain
chain = SingleLLMChain(llm)


def ask_about_schedule(question):
    # Example: summarize the calendar data or fetch specific entries
    context = f"My schedule for the week includes: {json.dumps(calendar_data)}"  # You might want to format this better

    # Generate a response using Langchain
    response = chain.run_chain(input_text=f"{context} {question}")
    return response


print(ask_about_schedule("What meetings do I have on Monday?"))
