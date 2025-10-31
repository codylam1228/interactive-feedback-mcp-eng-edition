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


class FeedbackResult(TypedDict):
    """Type definition for feedback result structure"""
    interactive_feedback: str
    images: List[str]


def launch_feedback_ui(summary: str, predefinedOptions: Optional[List[str]] = None) -> FeedbackResult:
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
        args = [
            sys.executable,
            "-u",
            feedback_ui_path,
            "--prompt", summary,
            "--output-file", output_file,
            "--predefined-options", json.dumps(predefinedOptions) if predefinedOptions else ""
        ]
        result = subprocess.run(
            args,
            check=False,
            shell=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            timeout=300  # 5 minute timeout to prevent indefinite hanging
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
            raise Exception(f"Failed to launch feedback UI (code {result.returncode}): {stderr}")

        # Wait for output file to be written (with timeout)
        max_wait = 5  # seconds
        waited = 0
        while not os.path.exists(output_file) and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
        
        if not os.path.exists(output_file):
            raise Exception("Feedback UI did not produce output file")

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
    result_dict = launch_feedback_ui(message, predefined_options_list)

    txt: str = result_dict.get("interactive_feedback", "").strip()
    img_b64_list: List[str] = result_dict.get("images", [])

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
