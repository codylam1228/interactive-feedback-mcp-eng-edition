# 🗣️ Interactive Feedback MCP

An [MCP Server](https://modelcontextprotocol.io/) that enables interactive, multi-turn conversations between you and AI assistants (like in [Cursor](https://www.cursor.com), [Cline](https://cline.bot), and [Windsurf](https://windsurf.com)) within a single API request, allowing iterative refinement without consuming additional premium API calls.

## 🎯 Key Features

- **🔄 Continuous Feedback Loop**: The AI can repeatedly call `interactive_feedback` to engage in a multi-turn conversation within a single API request, allowing for iterative refinement until you're satisfied. You control when to stop using the "End" button.

- **🖼️ Image Upload Support**: Paste images directly into the feedback field. Images are automatically converted to base64 format and sent to the AI, enabling visual context and image-based communication.

- **✅ Predefined Options**: The AI can present predefined options as checkboxes for quick decision-making, streamlining common choices and reducing typing.

- **⚙️ System Default Prompt**: Editable textbox that allows you to set persistent default instructions that are automatically included with every feedback submission. Your custom prompt is saved across sessions.

- **⌨️ Keyboard Shortcuts**: Quick actions like `Ctrl+Enter` (or `Cmd+Enter` on Mac) to submit, font zoom controls, and line height adjustments for a smooth user experience.

- **💰 Zero Additional API Costs**: All feedback interactions happen within a single API request cycle. Tool calls don't count as separate premium interactions, so you can iterate freely without consuming your monthly request limit.
**Note:** This server is designed to run locally alongside the MCP client (e.g., Claude Desktop, VS Code), as it needs direct access to the user's operating system to display notifications.

## New Features

- Beautiful UI
- Support pasting images
- Support markdown format
- **System default prompt**: Editable textbox that allows you to set a default prompt that gets automatically included with every feedback submission. This prompt is persisted across sessions and can be reset to the server default at any time.
- **End button**: Red "End" button that signals the AI to finalize the response and stop the feedback loop, preventing further `interactive_feedback` tool calls in the current session.

## 🖼️ **Interactive Feedback Window**
This image shows the interactive feedback dialog window that appears when the AI assistant calls the `interactive_feedback` tool. The window displays a question or prompt from the AI, allowing you to provide clarification, select from predefined options, or paste images directly into the feedback field. The modern UI supports markdown formatting, making it easy to provide detailed feedback. The window also includes a "System default prompt" textbox for setting persistent default instructions, and an "End" button to signal the AI to finalize the response.

![Interactive Feedback window](./image1.jpg)

## 💡 Why Use This?

- **💰 Reduced Premium API Calls:** Avoid wasting expensive API calls generating code based on guesswork.
- **✅ Fewer Errors:** Clarification _before_ action means less incorrect code and wasted time.
- **⏱️ Faster Cycles:** Quick confirmations beat debugging wrong guesses.
- **🎮 Better Collaboration:** Turns one-way instructions into a dialogue, keeping you in control.

## 🛠️ Tools

This server exposes the following tool via the Model Context Protocol (MCP):

- `interactive_feedback`: Asks the user a question and returns their answer. Can display predefined options.

## ✨ Key Features

### 1. System Default Prompt

The feedback window includes an editable "System default prompt" textbox that allows you to set persistent instructions that are automatically included with every feedback submission. This is useful for:

- Setting default behavior instructions for the AI (e.g., "Always maintain an active feedback loop...")
- Providing context that should be included in every interaction
- Customizing the AI's default response style

The default prompt is:
- **Persisted across sessions**: Your custom prompt is saved and will appear in future feedback windows
- **Reset to server default**: Use the "Reset to server default" button to restore the original server-provided default prompt
- **Combined with your feedback**: The system default prompt is automatically prepended to your feedback text when submitting

### 2. Button Usage

The feedback window has several buttons:

**In the System Default Prompt section:**
- **Reset to server default**: Restores the system default prompt textbox to the original server-provided default value, discarding any custom edits you've made.

**At the bottom of the window:**
- **Submit** (Blue): Sends your feedback to the AI and continues the conversation. You can also press `Ctrl+Enter` (or `Cmd+Enter` on Mac) to submit.
- **End** (Red): Sends your feedback and signals the AI to finalize the response, stopping the feedback loop for this session.
- **Cancel** (Grey): Closes the window without sending any feedback, effectively canceling the interaction.

## 📦 Installation

1.  **Prerequisites:**
    - Python 3.10+
    - [uv](https://github.com/astral-sh/uv) (Python package manager). 
    
2.  **Get the code:**
    - Clone this repository:
      `git clone https://github.com/codylam1228/interactive-feedback-mcp-eng-edition.git`
    - Or download the source code.

## ⚙️ Configuration

1. Add the following configuration to your `claude_desktop_config.json` (Claude Desktop) or `mcp.json` (Cursor):
   **Remember to change the `/path/to/interactive-feedback-mcp-eng-edition` path to the actual path where you cloned the repository on your system.**

```json
{
  "mcpServers": {
    "interactive-feedback": {
      "command": "uv",
      "args": [
        "--directory", 
        "</path/to/interactive-feedback-mcp-eng-edition>", 
        "run", 
        "server.py"],
      "timeout": 600,
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

## 🙏 Acknowledgements

This project is an English edition maintained by [codylam1228](https://github.com/codylam1228).

It is a fork with the following lineage:
1.  Forked from [kele527/interactive-feedback-mcp](https://github.com/kele527/interactive-feedback-mcp) (UI Optimization by [@kele527](https://x.com/jasonya76775253))
2.  Who forked from [poliva/interactive-feedback-mcp](https://github.com/poliva/interactive-feedback-mcp) (Enhanced by Pau Oliva [@pof](https://x.com/pof))
3.  Who forked from [noopstudios/interactive-feedback-mcp](https://github.com/noopstudios/interactive-feedback-mcp) (Original development by Fábio Ferreira [@fabiomlferreira](https://x.com/fabiomlferreira))
4. (Current) [codylam1228/interactive-feedback-mcp-eng-edition](https://github.com/codylam1228/interactive-feedback-mcp-eng-edition)