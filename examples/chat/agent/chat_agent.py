from datetime import datetime
from email import message

# from agent.src.pig_subgraph import tools
from .pig_agent import PigAgent
from .utils import ensure_tools_resolved

from langgraph.graph import MessagesState
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, AIMessageChunk, HumanMessageChunk, SystemMessage
from langgraph.graph import END, START, StateGraph
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode


class ChatAgent():
    def __init__(
        self, 
        pig_client, 
        pig_machine_id,
        chat_llm, 
        chat_system_prompt,
        computer_use_llm,
        computer_use_system_prompt
    ):
        self.chat_llm = chat_llm
        self.chat_system_prompt = chat_system_prompt
        self.computer_use_system_prompt = computer_use_system_prompt
        self.pig_agent = PigAgent(pig_client, pig_machine_id, computer_use_llm)

        self.chat_llm = self.chat_llm.bind_tools([self.call_pig_agent])

        self.graph = (
            StateGraph(MessagesState)
            .add_node("call_model", self.call_model)
            .add_node("prompt_user", self.prompt_user)
            .add_node("call_pig_agent", self.call_pig_agent_node)
            .add_edge(START, "prompt_user")
            .add_edge("prompt_user", "call_model")
            .add_conditional_edges("call_model", self.route, ["call_model", "prompt_user", "call_pig_agent", END])
            .add_edge("call_pig_agent", "call_model")
            .compile()
        )

    # Router
    def route(self, state: MessagesState) -> str:
        if not state["messages"]:
            return "call_model"
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            # Assumes only one tool call
            return last_message.tool_calls[0]["name"]

        return "prompt_user"

    # Nodes
    def call_model(self, state: MessagesState):

        messages = ensure_tools_resolved(state["messages"])

        response = self.chat_llm.invoke(
            messages
        )
        return {"messages": [response]}

    def prompt_user(self, state: MessagesState):
        user_input = input()
        print()
        return {"messages": [HumanMessage(user_input)]}

    # Tool Nodes
    
    @tool
    @staticmethod
    def call_pig_agent(task: str) -> str:
        """Calls the pig subagent with a task"""
        # Simply used to provide documentation to the LLM for the tool
        pass

    # Actual Tool function we call (since we use self)
    def call_pig_agent_node(self, state: MessagesState):
        tool_call = state["messages"][-1].tool_calls[0]
        task = tool_call["args"].get("task")

        result = self.pig_agent.graph.invoke({"messages": [
            SystemMessage(content=self.computer_use_system_prompt),
            HumanMessage(task)
        ]},
        {'recursion_limit': 500}
        )
    
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=result["messages"][-1].content
            )
        }



    def run(self):
        print("\033[34m" + "How could I help you?\nTry something like: 'describe the screen' or 'open the file explorer'\n" + "\033[0m")

        initial_state = {"messages": [SystemMessage(content=self.chat_system_prompt)]}
        prev_content_type = None
        for message_chunk, _ in self.graph.stream(
            initial_state,
            stream_mode="messages",
        ):
            if isinstance(message_chunk, AIMessageChunk):
                if message_chunk.content:
                    if isinstance(message_chunk.content, str):
                        # Add linebreak when transitioning from list (subgraph) to str (graph)
                        if prev_content_type == "list":
                            print("\n\n", end="", flush=True)
                        print("\033[34m" + message_chunk.content + "\033[0m", end="", flush=True)
                        prev_content_type = "str"
                    elif isinstance(message_chunk.content, list):
                        for item in message_chunk.content:
                            if item["type"] == "text":
                                print("\033[35m" + item["text"] + "\033[0m", end="", flush=True)
                            elif item["type"] == "tool_use" and item.get("name"):
                                print(f"\n\nTool: {item['name']}\n")
                        prev_content_type = "list"
                else:
                    if message_chunk.response_metadata.get("finish_reason") == "stop":
                        print("\n\n", end="", flush=True)
                        prev_content_type = None  # Reset for next conversation turn
