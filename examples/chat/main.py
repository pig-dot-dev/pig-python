from agent import ChatAgent

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pig import Client

# Choose our LLMs, compatible with Langchain Chat models.
chat_llm = ChatOpenAI(model="gpt-4o")
computer_use_llm = ChatAnthropic(model="claude-3-7-sonnet-20250219")

# Initialize our Pig client.
pig_client = Client()

machine_id = "your_machine_id"

# Initialize our agent.
agent = ChatAgent(
    pig_client=pig_client,
    pig_machine_id=machine_id,
    chat_llm=chat_llm,
    computer_use_llm=computer_use_llm,
)

# Run the agent. Will prompt for user input, and print the output.
agent.run()