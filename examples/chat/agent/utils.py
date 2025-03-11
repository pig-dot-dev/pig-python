from typing import List
from langchain_core.messages import BaseMessage, ToolMessage, AIMessage

def ensure_tools_resolved(messages: List[BaseMessage]) -> List[BaseMessage]:
    unresolved_ids = set()
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                unresolved_ids.add(tool_call["id"])
        if isinstance(message, ToolMessage):
            unresolved_ids.discard(message.tool_call_id)

    for unresolved_id in unresolved_ids:
        messages.append(ToolMessage(tool_call_id=unresolved_id, content="tool call ignored"))

    return messages
