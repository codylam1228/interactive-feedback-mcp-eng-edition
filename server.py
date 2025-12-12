# Interactive Feedback MCP
# Developed by Fábio Ferreira (https://x.com/fabiomlferreira)
# Inspired by/related to dotcursorrules.com (https://dotcursorrules.com/)
# Enhanced by Pau Oliva (https://x.com/pof) with ideas from https://github.com/ttommyth/interactive-mcp
import os
import sys
import json
import tempfile
import subprocess
import base64
import time
from typing import Any, Dict, List, Optional, TypedDict

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from mcp.types import ContentBlock, TextContent
from pydantic import Field

# Set log_level to ERROR to suppress verbose logs that interfere with Cline's MCP protocol parsing
# See: https://github.com/jlowin/fastmcp/issues/81
mcp = FastMCP("Interactive Feedback MCP")

# Default system prompt shown in the new “System default prompt” textbox
DEFAULT_SYSTEM_PROMPT = (
    "CRITICAL INSTRUCTION: You must maintain an active feedback loop. "
    "For EVERY response, strictly follow this sequence: "
    "1. Provide a concise answer or acknowledgement. "
    "2. Ask a targeted follow-up question to refine, confirm, or explore next steps. "
    "3. IMMEDIATELY invoke the 'interactive-feedback' tool with that question. "
    "NEVER skip the tool call. NEVER provide a text-only response. "
    "Even if the task seems complete, or the user says 'thanks', you MUST ask 'Is there anything else?' via the tool. "
    "Do not terminate the interaction until the user explicitly confirms satisfaction. "
    "Your response is incomplete without the interactive-feedback tool call."
)

class FeedbackResult(TypedDict):
    """Type definition for feedback result structure"""
    interactive_feedback: str
    images: List[str]
    end_session: bool


def launch_feedback_ui(
    summary: str,
    predefinedOptions: Optional[List[str]] = None,
    default_prompt: Optional[str] = None,
) -> FeedbackResult:
    # Create a temporary file for the feedback result
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_file = tmp.name

    try:
        # Get the path to feedback_ui.py relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        feedback_ui_path = os.path.join(script_dir, "feedback_ui.py")
        
        # Validate that feedback_ui.py exists
        if not os.path.exists(feedback_ui_path):
            raise FileNotFoundError(f"feedback_ui.py not found at: {feedback_ui_path}")

        # Run feedback_ui.py as a separate process
        # NOTE: There appears to be a bug in uv, so we need
        # to pass a bunch of special flags to make this work
        # Use JSON encoding for predefined_options to safely handle special characters
        # Use Base64 encoding for prompt to avoid command line parsing issues (e.g. with - characters)
        prompt_b64 = base64.b64encode(summary.encode("utf-8")).decode("utf-8")
        default_prompt_str = default_prompt or ""
        default_prompt_b64 = base64.b64encode(default_prompt_str.encode("utf-8")).decode(
            "utf-8"
        )
        
        args = [
            sys.executable,
            "-u",
            feedback_ui_path,
            "--encoded-prompt", prompt_b64,
            "--output-file", output_file,
            "--predefined-options", json.dumps(predefinedOptions) if predefinedOptions else "",
            "--default-prompt", default_prompt_b64,
        ]
        result = subprocess.run(
            args,
            check=False,
            shell=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
            raise Exception(f"Failed to launch feedback UI (code {result.returncode}): {stderr}")

        # Check if output file exists and has content
        if not os.path.exists(output_file):
            # Treat a missing file as a user-cancelled window instead of an error
            return FeedbackResult(interactive_feedback="", images=[], end_session=False)

        # Read the result from the temporary file
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse feedback result JSON: {e}")
        except IOError as e:
            raise Exception(f"Failed to read feedback result file: {e}")
        
        # Validate result structure
        if not isinstance(result_data, dict):
            raise ValueError("Invalid feedback result: expected dict")
        if "interactive_feedback" not in result_data:
            result_data["interactive_feedback"] = ""
        if "images" not in result_data:
            result_data["images"] = []
        if "end_session" not in result_data:
            result_data["end_session"] = False
        
        return result_data
    finally:
        # Guaranteed cleanup in all cases
        if os.path.exists(output_file):
            try:
                os.unlink(output_file)
            except OSError:
                pass  # Best effort cleanup

@mcp.tool()
def interactive_feedback(
    message: str = Field(description="The specific question for the user"),
    predefined_options: Optional[List[str]] = Field(default=None, description="Predefined options for the user to choose from (optional)"),
) -> List[ContentBlock]:
    """
    Request interactive feedback from the user.
    """
    predefined_options_list = predefined_options if isinstance(predefined_options, list) else None
    error_message: Optional[str] = None
    try:
        result_dict = launch_feedback_ui(
            message,
            predefined_options_list,
            default_prompt=DEFAULT_SYSTEM_PROMPT,
        )
    except Exception as e:
        error_message = f"[error] Feedback UI failed: {e}"

    if error_message:
        return [TextContent(type="text", text=error_message)]

    txt: str = result_dict.get("interactive_feedback", "").strip()
    img_b64_list: List[str] = result_dict.get("images", [])
    end_session: bool = bool(result_dict.get("end_session", False))

    if end_session:
        stop_note = "User selected End. Finalize the response now and do not call the interactive_feedback tool again."
        txt = f"{txt}\n\n{stop_note}" if txt else stop_note

    # Convert base64 to Image objects
    images: List[Image] = []
    for idx, b64 in enumerate(img_b64_list, start=1):
        try:
            img_bytes = base64.b64decode(b64)
            # TODO: feedback_ui.py doesn't pass back the actual image format, 
            # so we assume PNG. Consider enhancing the protocol to include format info.
            images.append(Image(data=img_bytes, format="png"))
        except Exception as e:
            # If decoding fails, ignore the image and notify in text with specifics
            warning = f"[warning] Image {idx} failed to decode: {str(e)}"
            txt = f"{txt}\n\n{warning}" if txt else warning

    # Assemble tuple based on actual returned content
    contents: List[ContentBlock] = []

    if txt:
        contents.append(TextContent(type="text", text=txt))

    for image in images:
        contents.append(image.to_image_content())

    if not contents:
        contents.append(TextContent(type="text", text=""))

    return contents

if __name__ == "__main__":
    mcp.run(transport="stdio", log_level="ERROR")
