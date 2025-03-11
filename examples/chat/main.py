from agent import ChatAgent
from agent.prompts import chat_system_prompt, pig_system_prompt
import os
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pig import Client

# Choose our LLMs, compatible with Langchain Chat models.
chat_llm = ChatOpenAI(model="gpt-4o") # For the outer chat loop

computer_use_llm = ChatAnthropic( # For computer use agent
    model="claude-3-7-sonnet-20250219", 
    temperature=0.1, 
    max_retries=50
)

# Initialize our Pig client.
pig_client = Client()

machine_id = os.getenv("PIG_MACHINE_ID")
if not machine_id:
    raise Exception("PIG_MACHINE_ID environment variable must be set")

# Initialize our agent.
agent = ChatAgent(
    pig_client=pig_client,
    pig_machine_id=machine_id,
    chat_llm=chat_llm,
    chat_system_prompt=chat_system_prompt,
    computer_use_llm=computer_use_llm,
    computer_use_system_prompt=pig_system_prompt
)

# Run the agent with system prompts. Will prompt for user input, and print the output.
agent.run()