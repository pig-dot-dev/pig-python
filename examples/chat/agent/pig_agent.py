from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage


class PigAgent():
    def __init__(self, pig_client, pig_machine_id, computer_use_llm):
        self.client = pig_client
        self.machine_id = pig_machine_id
        self.computer_use_llm = computer_use_llm
        self.connection = None
        self.dims = None

        tools = [self.get_dimensions]
        self.computer_use_llm = self.computer_use_llm.bind_tools(tools)

        self.graph = (
            StateGraph(MessagesState)
            .add_node("call_model", self.call_model)
            .add_node("get_dimensions", self.get_dimensions_node)
            .add_node("create_connection", self.create_connection)
            .add_edge(START, "create_connection")
            .add_edge("create_connection", "call_model")
            .add_conditional_edges("call_model", self.route, ["get_dimensions", END])
            .add_edge("get_dimensions", "call_model")
            .compile()
        )

    def create_connection(self, state: MessagesState):
        machine = self.client.machines.get(self.machine_id)
        self.connection = self.client.connections.create(machine)
        self.dims = self.connection.dimensions()

    def call_model(self, state: MessagesState):
        response = self.computer_use_llm.invoke(state["messages"])
        return {"messages": [response]}

    # Router
    def route(self, state: MessagesState) -> str:
        if not state["messages"]:
            return "call_model"
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            # assume one tool call
            return last_message.tool_calls[0]["name"]

        return END

    
    # Tools
    @tool
    @staticmethod
    def get_dimensions() -> str:
        "get the screen dimensions"
        pass

    def get_dimensions_node(self, state: MessagesState) -> str:
        tool_call = state["messages"][-1].tool_calls[0]

        # Actual implemntation
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"got dimensions: {self.dims}"
            )
        }