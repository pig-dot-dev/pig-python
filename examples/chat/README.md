# Windows Computer Use Chat Example

This example runs a chat agent, which can trigger a computer-use agent with a high level task to perform on a connected Windows machine. 

The computer-use agent uses SDK functions provided by Pig's SDK as its tools for `click`, `screenshot`, and more.

The agent and sub-agent are implemented in [LangGraph](https://www.langchain.com/langgraph) using [LangChain](https://www.langchain.com) chat models, and both `OpenAI GPT-4o` and `Anthropic Claude-3.7 Computer Use` are used as the chat and computer-use llms respectively, though you're free to swap out implementations.

## Prerequisites
- A Pig account (free tier available)
- A connected Windows machine, using [Piglet](https://github.com/pig-dot-dev/piglet). Follow [this guide](https://docs.pig.dev/quickstart/intro) to connect your machine.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
   
Get your Pig secret key from [Keys](https://pig.dev/app/keys)

Get your Pig machine ID by clicking into your connected machine in [the Machines page](https://pig.dev/app), and copy the ID the looks like `M-YOUR-MACHINE-ID`

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export PIG_SECRET_KEY="your-api-key"
export PIG_MACHINE_ID="your-machine-id"
```


3. Run the agent:
```bash
python main.py
```

Feel free to explore the code in [./agent](./agent) or tweak the prompts in [./agent/prompts](./agent/prompts)
