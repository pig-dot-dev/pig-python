from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, BaseMessage
import base64
from typing import Optional, Tuple, Dict, List
from .utils import ensure_tools_resolved

class PigAgent():
    def __init__(self, pig_client, pig_machine_id, computer_use_llm):
        self.client = pig_client
        self.machine_id = pig_machine_id
        self.computer_use_llm = computer_use_llm
        self.connection = None
        self.dims = None
        
        # Model's trained dimensions (Claude's assumption)
        self.model_trained_w, self.model_trained_h = 1024, 768
        # Actual screen dimensions will be set in create_connection
        self.screen_w, self.screen_h = None, None

        tools = [
            self.get_dimensions,
            self.cursor_position,
            self.screenshot,
            self.type_text,
            self.key_press,
            self.mouse_move,
            self.left_click,
            self.right_click,
            self.double_click,
            self.left_click_drag
        ]
        self.computer_use_llm = self.computer_use_llm.bind_tools(tools)

        self.graph = (
            StateGraph(MessagesState)
            .add_node("call_model", self.call_model)
            .add_node("get_dimensions", self.get_dimensions_node)
            .add_node("cursor_position", self.cursor_position_node)
            .add_node("screenshot", self.screenshot_node)
            .add_node("type_text", self.type_text_node)
            .add_node("key_press", self.key_press_node)
            .add_node("mouse_move", self.mouse_move_node)
            .add_node("left_click", self.left_click_node)
            .add_node("right_click", self.right_click_node)
            .add_node("double_click", self.double_click_node)
            .add_node("left_click_drag", self.left_click_drag_node)
            .add_node("create_connection", self.create_connection)
            .add_edge(START, "create_connection")
            .add_edge("create_connection", "call_model")
            .add_conditional_edges(
                "call_model", 
                self.route, 
            )
            .add_edge("get_dimensions", "call_model")
            .add_edge("cursor_position", "call_model")
            .add_edge("screenshot", "call_model")
            .add_edge("type_text", "call_model")
            .add_edge("key_press", "call_model")
            .add_edge("mouse_move", "call_model")
            .add_edge("left_click", "call_model")
            .add_edge("right_click", "call_model")
            .add_edge("double_click", "call_model")
            .add_edge("left_click_drag", "call_model")
            .compile()
        )

    def create_connection(self, state: MessagesState):
        machine = self.client.machines.get(self.machine_id)
        self.connection = self.client.connections.create(machine)
        self.dims = self.connection.dimensions()
        
        # Set screen dimensions for coordinate scaling
        self.screen_w, self.screen_h = self.dims

    def call_model(self, state: MessagesState):

        messages = ensure_tools_resolved(state["messages"])
        
        response = self.computer_use_llm.invoke(messages)
        return {"messages": [response]}
    
    # Router
    def route(self, state: MessagesState) -> str:
        if not state["messages"]:
            return "call_model"
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            # assume one tool call
            return last_message.tool_calls[0]["name"] # requires tool name to map to a node of the same name, with implementation

        return END

    
    # Tools
    @tool
    @staticmethod
    def get_dimensions() -> str:
        """Get the screen dimensions of the remote machine.
        Returns the width and height of the screen in pixels."""
        pass

    def get_dimensions_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]

        # Actual implementation
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Screen dimensions: width={self.dims[0]}, height={self.dims[1]} pixels"
            )
        }
        
    @tool
    @staticmethod
    def cursor_position() -> str:
        """Get the current x,y coordinates of the mouse cursor on screen. Use this to:
        1. Check cursor location before performing mouse actions
        2. Verify cursor movement results
        3. Get cursor position for relative movements
        Returns a string with format 'Mouse coordinates: x=<x>, y=<y>'"""
        pass
        
    def cursor_position_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        
        # Get current cursor position in screen coordinates
        x, y = self.connection.cursor_position()
        
        # Convert to model coordinates
        model_x, model_y = self.to_model_coordinates(x, y)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Mouse coordinates: x={model_x}, y={model_y}"
            )
        }
        
    @tool
    @staticmethod
    def screenshot() -> List[Dict]:
        """Capture the current screen state as an image. Useful for:
        1. Visual verification of UI state
        2. OCR and image analysis tasks
        3. Debugging user interface interactions
        Returns a base64 encoded PNG image"""
        pass
        
    def screenshot_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        
        # Capture screenshot
        screenshot_bytes = self.connection.screenshot()
        image_data = base64.b64encode(screenshot_bytes).decode()
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}]
            )
        }
        
    @tool
    @staticmethod
    def type_text(text: str) -> str:
        """Type text into the active window as if typed by a human keyboard.
        Use this for text input rather than key_press when typing normal text.
        The text will be typed exactly as provided, including spaces and special characters.
        Does not automatically press the enter/return key after typing.
        
        Args:
            text: The text to type
            
        Returns:
            Confirmation message with the text that was typed.
        """
        pass
        
    def type_text_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        text = tool_call["args"].get("text", "")
        
        # Type the text
        self.connection.type(text)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Typed text: {text}"
            )
        }
        
    @tool
    @staticmethod
    def key_press(combo: str) -> str:
        """Send keyboard combinations or special keys to the machine.
        Examples:
        - Single keys: 'Return', 'Tab', 'Escape'
        - Special keys: 'super', 'super+Tab', 'alt+Tab'
        - Modifier combinations: 'ctrl+c', 'shift+alt+Tab'
        - Multiple combos: 'ctrl+c ctrl+v'
        Use this for keyboard shortcuts and special keys rather than regular text input.
        
        Args:
            combo: The key combination to press
            
        Returns:
            Confirmation message with the key combo that was pressed.
        """
        pass
        
    def key_press_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        combo = tool_call["args"].get("combo", "")
        
        # Press the key combination
        self.connection.key(combo)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Pressed key combo: {combo}"
            )
        }
        
    @tool
    @staticmethod
    def mouse_move(x: int, y: int) -> str:
        """Move the mouse cursor to absolute screen coordinates (x,y).
        Coordinate system: (0,0) is top-left of screen, x increases right, y increases down.
        Use cursor_position() first to help calculate relative movements.
        
        Args:
            x: The x-coordinate to move to
            y: The y-coordinate to move to
            
        Returns:
            Confirmation message with the coordinates the mouse moved to.
        """
        pass
        
    def mouse_move_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        model_x = tool_call["args"].get("x")
        model_y = tool_call["args"].get("y")
        
        # Convert from model coordinates to screen coordinates
        screen_x, screen_y = self.to_screen_coordinates(model_x, model_y)
        
        # Move the mouse
        self.connection.mouse_move(screen_x, screen_y)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Moved mouse to: x={model_x}, y={model_y}"
            )
        }
        
    @tool
    @staticmethod
    def left_click(x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Perform a left mouse click. Two modes of operation:
        1. If x,y provided: First moves to (x,y), then clicks
        2. If no coordinates: Clicks at current cursor position
        Use for most standard UI interactions like button clicks.
        
        Args:
            x: Optional x-coordinate to click at
            y: Optional y-coordinate to click at
            
        Returns:
            Confirmation message with the coordinates that were clicked.
        """
        pass
        
    def left_click_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        model_x = tool_call["args"].get("x")
        model_y = tool_call["args"].get("y")
        
        # Convert from model coordinates to screen coordinates
        screen_x, screen_y = self.to_screen_coordinates(model_x, model_y)
        
        # Perform left click
        self.connection.left_click(screen_x, screen_y)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Left clicked at: x={model_x if model_x is not None else 'current'}, y={model_y if model_y is not None else 'current'}"
            )
        }
        
    @tool
    @staticmethod
    def right_click(x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Perform a right mouse click. Two modes of operation:
        1. If x,y provided: First moves to (x,y), then clicks
        2. If no coordinates: Clicks at current cursor position
        Use for context menus and alternative actions.
        
        Args:
            x: Optional x-coordinate to click at
            y: Optional y-coordinate to click at
            
        Returns:
            Confirmation message with the coordinates that were clicked.
        """
        pass
        
    def right_click_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        model_x = tool_call["args"].get("x")
        model_y = tool_call["args"].get("y")
        
        # Convert from model coordinates to screen coordinates
        screen_x, screen_y = self.to_screen_coordinates(model_x, model_y)
        
        # Perform right click
        self.connection.right_click(screen_x, screen_y)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Right clicked at: x={model_x if model_x is not None else 'current'}, y={model_y if model_y is not None else 'current'}"
            )
        }
        
    @tool
    @staticmethod
    def double_click(x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Perform a double left click. Two modes of operation:
        1. If x,y provided: First moves to (x,y), then double clicks
        2. If no coordinates: Double clicks at current cursor position
        Use for actions that typically require double clicks like file opening.
        
        Args:
            x: Optional x-coordinate to double-click at
            y: Optional y-coordinate to double-click at
            
        Returns:
            Confirmation message with the coordinates that were double-clicked.
        """
        pass
        
    def double_click_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        model_x = tool_call["args"].get("x")
        model_y = tool_call["args"].get("y")
        
        # Convert from model coordinates to screen coordinates
        screen_x, screen_y = self.to_screen_coordinates(model_x, model_y)
        
        # Perform double click
        self.connection.double_click(screen_x, screen_y)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Double clicked at: x={model_x if model_x is not None else 'current'}, y={model_y if model_y is not None else 'current'}"
            )
        }
        
    @tool
    @staticmethod
    def left_click_drag(x: int, y: int) -> str:
        """Click and drag from current position to target coordinates.
        Process:
        1. Holds left button down at current position
        2. Moves cursor to target x,y
        3. Releases left button
        Use for drag-and-drop operations or selection areas.
        
        Args:
            x: The x-coordinate to drag to
            y: The y-coordinate to drag to
            
        Returns:
            Confirmation message with the coordinates that were dragged to.
        """
        pass
        
    def left_click_drag_node(self, state: MessagesState) -> Dict:
        tool_call = state["messages"][-1].tool_calls[0]
        model_x = tool_call["args"].get("x")
        model_y = tool_call["args"].get("y")
        
        # Convert from model coordinates to screen coordinates
        screen_x, screen_y = self.to_screen_coordinates(model_x, model_y)
        
        # Perform click and drag
        self.connection.left_click_drag(screen_x, screen_y)
        
        return {
            "messages": ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"Dragged mouse from current position to: x={model_x}, y={model_y}"
            )
        }


    
    # Coordinate conversion utilities
    def to_screen_coordinates(self, model_x: Optional[int], model_y: Optional[int]) -> Tuple[Optional[int], Optional[int]]:
        """Convert model coordinates (1024x768) to actual screen coordinates."""
        if model_x is None or model_y is None:
            return None, None
            
        screen_x = int(model_x * self.screen_w / self.model_trained_w)
        screen_y = int(model_y * self.screen_h / self.model_trained_h)
        
        # Clamp to screen bounds
        screen_x = max(0, min(screen_x, self.screen_w - 1))
        screen_y = max(0, min(screen_y, self.screen_h - 1))
        
        return screen_x, screen_y
    
    def to_model_coordinates(self, screen_x: Optional[int], screen_y: Optional[int]) -> Tuple[Optional[int], Optional[int]]:
        """Convert actual screen coordinates to model coordinates (1024x768)."""
        if screen_x is None or screen_y is None:
            return None, None
            
        model_x = int(screen_x * self.model_trained_w / self.screen_w)
        model_y = int(screen_y * self.model_trained_h / self.screen_h)
        
        # Clamp to model bounds
        model_x = max(0, min(model_x, self.model_trained_w - 1))
        model_y = max(0, min(model_y, self.model_trained_h - 1))
        
        return model_x, model_y
