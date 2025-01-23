from typing import Literal, TypedDict
from pig import Connection
import base64
from io import BytesIO
from PIL import Image
from dataclasses import dataclass

from anthropic.types.beta import BetaToolComputerUse20241022Param

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "double_click",
    "screenshot",
    "cursor_position",

    # Special actions
    "yield_control",
]

class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None

@dataclass(kw_only=True, frozen=True)
class ToolResult:
    output: str | None = None
    error: str | None = None
    base64_image: str | None = None
    system: str | None = None

class PigComputerTool:
    name: Literal["computer"] = "computer"
    api_type: Literal["computer_20241022"] = "computer_20241022"
    width: int = 1024
    
    height: int = 768
    display_num: int | None = None

    @property
    def options(self) -> ComputerToolOptions:
        return {
            "display_width_px": self.width,
            "display_height_px": self.height,
            "display_number": self.display_num,
        }

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {"name": self.name, "type": self.api_type, **self.options}

    def __init__(self, connection: Connection):
        self.conn = connection

    def screenshot(self) -> bytes:
        """Take a screenshot of the current screen and return the base64 encoded image."""
        # Get BMP data from connection
        bmp_data = self.conn.screenshot()
        
        # Convert BMP to PNG using PIL
        image = Image.open(BytesIO(bmp_data))
        png_buffer = BytesIO()
        image.save(png_buffer, format="PNG")
        png_data = png_buffer.getvalue()
        
        # Create ToolResult with base64 encoded PNG
        return ToolResult(
            base64_image=base64.b64encode(png_data).decode()
        )
    
    async def __call__(
        self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        **kwargs,
    ) -> ToolResult:
        print(f"\naction: {action}")
        print(f"text: {text}")
        print(f"coordinate: {coordinate}")
        match action:
            case "key":
                self.conn.key(text)
                return ToolResult()
            case "type":
                self.conn.type(text)
                return ToolResult()
            case "mouse_move":
                self.conn.mouse_move(coordinate[0], coordinate[1])
                return ToolResult()
            case "left_click":
                self.conn.left_click()
                return ToolResult()
            case "left_click_drag":
                self.conn.left_click_drag(coordinate[0], coordinate[1])
                return ToolResult()
            case "right_click":
                self.conn.right_click()
                return ToolResult()
            case "double_click":
                self.conn.double_click()
                return ToolResult()

            # Return cases
            case "screenshot":
                return self.screenshot()

            case "cursor_position":
                x, y = self.conn.cursor_position()
                return ToolResult(output=f"X={x},Y={y}")

        raise Exception(f"Invalid action: {action}")


# from typing import Literal, TypedDict
# from pig import Connection
# from dataclasses import dataclass
# import base64
# from io import BytesIO
# from PIL import Image


class PigHelpTool:
    name: Literal["help"] = "help"
    description = "Request human intervention when needed for complex tasks or verification"
    
    def __init__(self, connection: Connection):
        self.conn = connection

    def to_params(self):
        """Return the tool parameters for the Anthropic API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get_human_help"],
                        "description": "Request human operator assistance"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message to display to the human operator"
                    }
                },
                "required": ["action"]
            }
        }

    async def __call__(
        self,
        *,
        action: Literal["get_human_help"],
        message: str | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute the help tool actions."""
        if action == "get_human_help":
            # Yield control to human operator
            self.conn.yield_control()
            self.conn.await_control()
            
            # Take screenshot after human intervention
            return ToolResult(
                output=f"Human operator assistance completed. Take a screenshot to see the results."
            )
        else:
            raise Exception(f"Invalid action: {action}")