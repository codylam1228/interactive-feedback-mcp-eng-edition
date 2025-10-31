# Interactive Feedback MCP UI
# Developed by Fábio Ferreira (https://x.com/fabiomlferreira)
# Inspired by/related to dotcursorrules.com (https://dotcursorrules.com/)
# Enhanced by Pau Oliva (https://x.com/pof) with ideas from https://github.com/ttommyth/interactive-mcp
import os
import sys
import json
import argparse
import base64
import uuid
import re  # Move re import to top
from datetime import datetime
from typing import Optional, TypedDict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QTextBrowser, QGroupBox,
    QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSettings, QUrl, QDateTime, QBuffer, QIODevice
from PySide6.QtGui import QTextCursor, QIcon, QKeyEvent, QPalette, QColor, QTextImageFormat, QTextDocument, QPixmap, QShortcut, QKeySequence, QFont

class FeedbackResult(TypedDict):
    interactive_feedback: str
    images: List[str]

def get_dark_mode_palette(app: QApplication):
    darkPalette = app.palette()
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.WindowText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
    darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    darkPalette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipText, Qt.white)
    darkPalette.setColor(QPalette.Text, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
    darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ButtonText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.BrightText, Qt.red)
    darkPalette.setColor(QPalette.Link, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    darkPalette.setColor(QPalette.HighlightedText, Qt.white)
    darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(127, 127, 127))
    darkPalette.setColor(QPalette.PlaceholderText, QColor(127, 127, 127))
    return darkPalette

class FeedbackTextEdit(QTextEdit):
    # Image processing constants
    DEFAULT_MAX_IMAGE_WIDTH = 1624
    DEFAULT_MAX_IMAGE_HEIGHT = 1624
    DEFAULT_IMAGE_FORMAT = "PNG"

    # Define class-level signals
    image_pasted = Signal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_data = []   # Store Base64 data list for images
        # Get device pixel ratio
        self.device_pixel_ratio = QApplication.primaryScreen().devicePixelRatio()
        # Image compression parameters
        self.max_image_width = self.DEFAULT_MAX_IMAGE_WIDTH  # Maximum width
        self.max_image_height = self.DEFAULT_MAX_IMAGE_HEIGHT  # Maximum height
        self.image_format = self.DEFAULT_IMAGE_FORMAT  # Image format

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            # Find the parent FeedbackUI instance and call submit
            parent = self.parent()
            while parent and not isinstance(parent, FeedbackUI):
                parent = parent.parent()
            if parent:
                parent._submit_feedback()
        else:
            super().keyPressEvent(event)

    def _convert_image_to_base64(self, image):
        """Convert image to Base64 encoded string"""
        try:
            # Convert image to QPixmap
            if not isinstance(image, QPixmap):
                pixmap = QPixmap.fromImage(image)
            else:
                pixmap = image

            # Create byte buffer
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)

            pixmap.save(buffer, self.image_format)
            file_extension = self.image_format.lower()  # Use lowercase format name as extension

            # Get byte data and convert to base64
            byte_array = buffer.data()
            base64_string = base64.b64encode(byte_array).decode('utf-8')
            buffer.close()

            # Return Base64 data and file extension
            return {
                'data': base64_string,
                'extension': file_extension
            }
        except Exception as e:
            print(f"Error converting image to Base64: {e}")
            return None

    # Add this method to handle pasting content, including images
    def insertFromMimeData(self, source_data):
        """
        Handle pasting from mime data, explicitly checking for image data.
        Support high DPI display for Retina Display
        """
        try:
            if source_data.hasImage():
                # If the mime data contains an image, convert to Base64
                image = source_data.imageData()
                if image:
                    try:
                        # Use original image without compression
                        # Convert image to Base64 encoding
                        image_result = self._convert_image_to_base64(image)

                        if image_result:
                            # Generate unique filename for identification
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            unique_id = str(uuid.uuid4())[:8]
                            filename = f"pasted_image_{timestamp}_{unique_id}.{image_result['extension']}"

                            # Save Base64 data
                            image_info = {
                                'base64': image_result['data'],
                                'filename': filename
                            }
                            self.image_data.append(image_info)

                            # Emit signal to notify parent component of new image paste
                            if isinstance(image, QPixmap):
                                pixmap = image
                            else:
                                pixmap = QPixmap.fromImage(image)
                            self.image_pasted.emit(pixmap)

                    except Exception as e:
                        print(f"Error processing image: {e}")
                        cursor = self.textCursor()
                        cursor.insertText(f"[Image processing failed: {str(e)}]")
                else:
                    cursor = self.textCursor()
                    cursor.insertText("[Image processing failed: Invalid image data]")
            elif source_data.hasHtml():
                # If the mime data contains HTML, insert it as HTML
                super().insertFromMimeData(source_data)
            elif source_data.hasText():
                # If the mime data contains plain text, insert it as plain text
                super().insertFromMimeData(source_data)
            else:
                # For other types, call the base class method
                super().insertFromMimeData(source_data)
        except Exception as e:
            print(f"Error processing pasted content: {e}")
            # Try using base class method
            try:
                super().insertFromMimeData(source_data)
            except:
                cursor = self.textCursor()
                cursor.insertText(f"[Paste content failed: {str(e)}]")

    def get_image_data(self):
        """Return image data list (including Base64 encoding)"""
        return self.image_data.copy()

class FeedbackUI(QMainWindow):
    # Cache Markdown instance
    _markdown_instance = None

    def __init__(self, prompt: str, predefined_options: Optional[List[str]] = None):
        super().__init__()
        self.prompt = prompt
        self.predefined_options = predefined_options or []

        self.feedback_result = None

        self.setWindowTitle("Cursor Interactive Feedback MCP")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "images", "feedback.png")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.settings = QSettings("InteractiveFeedbackMCP", "InteractiveFeedbackMCP")
        self.line_height = self._load_line_height()

        # Load general UI settings for the main window (geometry, state)
        self.settings.beginGroup("MainWindow_General")

        # Set window size to 60% of screen height, width remains 800
        screen = QApplication.primaryScreen().geometry()
        screen_height = screen.height()
        window_height = int(screen_height * 0.7)  # 60% of screen height
        window_width = 800

        # Set initial window size but allow user to adjust
        self.resize(window_width, window_height)

        # Set minimum window size to prevent UI elements from crowding
        self.setMinimumSize(600, 400)

        # Center window on screen
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.move(x, y)

        self.settings.endGroup() # End "MainWindow_General" group

        self._create_ui()
        self._setup_shortcuts()  # Add shortcut key settings

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text, handle escape character issues
        Special handling for escape characters from Cursor editor
        """
        # Record original text (for debugging)
        print(f"Original text: {repr(text)}")

        # Handle literal escape sequences
        if isinstance(text, str):
            # Try multiple decoding methods to handle escapes from different sources

            # Method 1: Try JSON decoding (for text passed from JSON parameters)
            try:
                import json
                # If text looks like a JSON-encoded string, try to decode it
                if '\\n' in text or '\\t' in text or '\\r' in text:
                    # Add quotes to make it a valid JSON string, then decode
                    decoded_text = json.loads(f'"{text}"')
                    print(f"JSON decoding successful: {repr(decoded_text)}")
                    text = decoded_text
                else:
                    print("No JSON decoding needed")
            except (json.JSONDecodeError, ValueError):
                print("JSON decoding failed, using string replacement method")
                # If JSON decoding fails, use string replacement method

                # First check if there are double escapes (like \\n)
                if '\\\\n' in text:
                    # Handle double-escaped newlines
                    text = text.replace('\\\\n', '\n')
                    text = text.replace('\\\\t', '\t')
                    text = text.replace('\\\\r', '\r')
                    text = text.replace('\\\\\\\\', '\\')  # Quadruple backslashes become single backslash
                else:
                    # 1. Handle literal escape sequences
                    text = text.replace('\\\\', '\\')  # Handle double backslashes first
                    text = text.replace('\\n', '\n')
                    text = text.replace('\\t', '\t')
                    text = text.replace('\\r', '\r')

            # 2. Normalize newlines
            text = text.replace('\r\n', '\n')
            text = text.replace('\r', '\n')

        # Record processed text (for debugging)
        print(f"Processed text: {repr(text)}")
        return text

    def _is_markdown(self, text: str) -> bool:
        """
        Detect if text might be Markdown format
        By checking common Markdown syntax features
        """
        # If text is empty, don't consider it Markdown
        if not text or text.strip() == "":
            return False

        # Preprocess text, handle escape characters
        text = self._preprocess_text(text)

        # Check common Markdown syntax features
        markdown_patterns = [
            r'^#{1,6}\s+.+',                  # Headers: # Header text
            r'\*\*.+?\*\*',                   # Bold: **text**
            r'\*.+?\*',                       # Italic: *text*
            r'_.+?_',                         # Italic: _text_
            r'`[^`]+`',                       # Inline code: `code`
            r'^\s*```',                       # Code block: ```
            r'^\s*>',                         # Quote: > text
            r'^\s*[-*+]\s+',                  # Unordered list: - item or * item or + item
            r'^\s*\d+\.\s+',                  # Ordered list: 1. item
            r'\[.+?\]\(.+?\)',                # Link: [text](URL)
            r'!\[.+?\]\(.+?\)',               # Image: ![alt](URL)
            r'\|.+\|.+\|',                    # Table
            r'^-{3,}$',                       # Horizontal line: ---
            r'^={3,}$',                       # Horizontal line: ===
        ]

        # Iterate through each line of text, check if it contains Markdown syntax features
        lines = text.split('\n')
        markdown_features_count = 0

        for line in lines:
            for pattern in markdown_patterns:
                if re.search(pattern, line, re.MULTILINE):
                    markdown_features_count += 1
                    # If clear Markdown features are found, return True immediately
                    if pattern in [r'^#{1,6}\s+.+', r'^\s*```', r'^\s*>', r'^\s*[-*+]\s+', r'^\s*\d+\.\s+', r'\|.+\|.+\|', r'^-{3,}$', r'^={3,}$']:
                        return True

        # If text contains a certain number of Markdown features, consider it Markdown
        # Here we judge based on the ratio of feature count to text length
        # If feature count exceeds 2 or feature density is high, consider it Markdown
        return markdown_features_count >= 2 or (markdown_features_count > 0 and markdown_features_count / len(lines) > 0.1)

    def _convert_text_to_html(self, text: str) -> str:
        """
        Convert plain text to HTML format
        Preserve line breaks and spaces, and perform basic HTML escaping
        """
        # Preprocess text, handle escape characters
        text = self._preprocess_text(text)

        # HTML escaping
        escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Preserve line breaks
        html_text = escaped_text.replace("\n", "<br>")

        # Apply styles, remove excessive indentation, add emoji font support
        # Reduce line height and use more specific font list for cross-platform consistency
        styled_html = f"""<div style="
            line-height: {self.line_height};
            color: #ccc;
            font-family: 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', system-ui, -apple-system, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji';
            white-space: pre-wrap;
        ">{html_text}</div>"""

        return styled_html

    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Use markdown library to convert markdown to HTML"""
        try:
            # Preprocess text, handle escape characters
            markdown_text = self._preprocess_text(markdown_text)

            import markdown
            from markdown.extensions import codehilite, tables, toc

            # Configure markdown extensions, add emoji support
            extensions = ['extra', 'codehilite', 'toc']

            # Try to add emoji extension (if available)
            try:
                import pymdownx.emoji
                extensions.append('pymdownx.emoji')
                extension_configs = {
                    'pymdownx.emoji': {
                        'emoji_index': pymdownx.emoji.gemoji,
                        'emoji_generator': pymdownx.emoji.to_svg,
                        'alt': 'short',
                        'options': {
                            'attributes': {
                                'align': 'absmiddle',
                                'height': '20px',
                                'width': '20px'
                            },
                            'image_path': 'https://assets-cdn.github.com/images/icons/emoji/unicode/',
                            'non_standard_image_path': 'https://assets-cdn.github.com/images/icons/emoji/'
                        }
                    }
                }
            except ImportError:
                print("pymdownx.emoji not available, using basic emoji support")
                extension_configs = {}

            # Use cached Markdown instance or create new instance
            if FeedbackUI._markdown_instance is None:
                FeedbackUI._markdown_instance = markdown.Markdown(
                    extensions=extensions,
                    extension_configs=extension_configs
                )

            # Reset instance to ensure state is cleared
            FeedbackUI._markdown_instance.reset()

            # Convert markdown to HTML
            html = FeedbackUI._markdown_instance.convert(markdown_text)

            # Apply custom styles, remove excessive indentation, add emoji support
            # Uniformly set base styles, reduce line height and paragraph spacing
            styled_html = f"""
            <style>
                /* Base styles */
                .md-content, .md-content p, .md-content li {{
                    line-height: {self.line_height} !important; /* Uniform and forced line height */
                    margin-top: 2px !important;
                    margin-bottom: 2px !important;
                }}
                .md-content {{
                    color: #ccc;
                    font-family: 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', system-ui, -apple-system, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji';
                    white-space: pre-wrap;
                }}

                /* Header styles */
                h1 {{ color: #FF9800; margin: 12px 0 8px 0; font-size: 1.3em; }}
                h2 {{ color: #2196F3; margin: 10px 0 6px 0; font-size: 1.2em; }}
                h3 {{ color: #4CAF50; margin: 10px 0 6px 0; font-size: 1.1em; }}

                /* List styles */
                ul, ol {{
                    margin: 6px 0;
                    padding-left: 20px;
                }}
                li {{
                    vertical-align: baseline;
                    display: list-item;
                    text-align: left;
                }}

                /* Code styles */
                code {{
                    background-color: rgba(255,255,255,0.1);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 0.9em;
                }}

                pre {{
                    background-color: rgba(255,255,255,0.05);
                    padding: 12px;
                    border-radius: 6px;
                    overflow-x: auto;
                    border-left: 4px solid #2196F3;
                }}

                /* Paragraph styles - already handled in .md-content p */
                p {{ }}

                /* Emphasis styles */
                strong {{ color: #FFD54F; }}
                em {{ color: #81C784; }}

                /* Emoji style optimization */
                .emoji, img.emoji {{
                    height: 1.2em;
                    width: 1.2em;
                    margin: 0 0.05em 0 0.1em;
                    vertical-align: -0.1em;
                    display: inline-block;
                }}

                /* Table styles */
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #444;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: rgba(255,255,255,0.1);
                    font-weight: bold;
                }}
            </style>
            <div class="md-content">{html}</div>
            """

            return styled_html

        except ImportError:
            # Fallback if markdown library is not installed
            # Log that markdown library is not found and basic conversion is used.
            print("Markdown library not found. Using basic HTML escaping for description.")
            return self._convert_text_to_html(markdown_text)
        except Exception as e:
            # Fallback for any other error during markdown conversion
            print(f"Error during markdown conversion: {e}. Using basic HTML escaping.")
            return self._convert_text_to_html(markdown_text)

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15,8,15,5)

        # Description text area (from self.prompt) - Support multiline, selectable and copyable with markdown support
        self.description_text = QTextBrowser()
        self._update_description_text()  # Call new method to set content

        # QTextBrowser is read-only by default, supports selection and copying
        self.description_text.setMaximumHeight(600)  # Set maximum height to prevent buttons from overflowing screen
        self.description_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Show scrollbar when needed
        self.description_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Set styles to make it look more like an information display area rather than an input box
        # Set styles for QTextBrowser to make it look more like an information display area
        self.description_text.setStyleSheet(
            "QTextBrowser {"
            # "  border: 1px solid #444444;"
            "  border-radius: 8px;"
            "  padding: 5px;"
            "  margin-bottom: 3px;"
            "  background-color: rgba(255, 255, 255, 0.05);"
            "  selection-background-color: #2196F3;"
            "}"
            "QTextBrowser:focus {"
            "  border: 1px solid #2196F3;"
            "}"
        )

        layout.addWidget(self.description_text)

        # Add predefined options if any
        self.option_checkboxes = []
        if self.predefined_options and len(self.predefined_options) > 0:
            options_frame = QFrame()
            options_layout = QVBoxLayout(options_frame)
            options_layout.setContentsMargins(0,5,0,10)

            for option in self.predefined_options:
                checkbox = QCheckBox(option)
                # Increase font size for checkboxes
                font = checkbox.font()
                font.setPointSize(font.pointSize())
                checkbox.setFont(font)
                self.option_checkboxes.append(checkbox)
                options_layout.addWidget(checkbox)

            layout.addWidget(options_frame)

        # Image preview area
        self.images_container = QFrame()
        self.images_container.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.images_container.setFixedHeight(80)  # Use fixed height
        self.images_layout = QHBoxLayout(self.images_container)
        self.images_layout.setSpacing(5)  # Reduce image spacing
        self.images_layout.setContentsMargins(0, 0, 0, 5)  # Remove padding
        self.images_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Left align and vertically center images
        self.images_container.setVisible(False)  # Hide by default

        # Add horizontal scroll support
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(80)  # Use fixed height
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)  # No border
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: rgba(0, 0, 0, 0.1);
                border-radius: 4px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #666;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        scroll_area.setWidget(self.images_container)
        scroll_area.setVisible(False)  # Hide scroll area by default
        self.scroll_area = scroll_area  # Save reference for visibility control
        layout.addWidget(scroll_area, 0)  # Use 0 as stretch factor to prevent auto-stretching
        # Reduce spacing between scroll area and other elements
        layout.setSpacing(2)  # Set smaller spacing for overall layout

        # Free-form text feedback
        self.feedback_text = FeedbackTextEdit()
        # Connect image paste signal
        self.feedback_text.image_pasted.connect(self._on_image_pasted)
        # Increase font size and apply modern border to text edit
        font = self.feedback_text.font()
        font.setPointSize(font.pointSize() )
        self.feedback_text.setFont(font)
        self.feedback_text.setStyleSheet(
            "QTextEdit {"
            "  border-radius: 8px;"
            "  padding: 0px;"
            "  margin: 0px 0 10px 0;"
            "  border: 1px solid #444444;"
            "  background-color: #222;"
            "}"
        )

        # Set a very small document margin, both beautiful and without obvious blank space
        document = self.feedback_text.document()
        document.setDocumentMargin(5)

        # Set minimum and maximum height, and scroll policy
        font_metrics = self.feedback_text.fontMetrics()
        row_height = font_metrics.height()
        # padding = self.feedback_text.contentsMargins().top() + self.feedback_text.contentsMargins().bottom() + 5

        # Minimum height: 5 lines of text
        min_height = 5 * row_height
        # Maximum height: 10 lines of text, prevent input box from being too high
        max_height = 10 * row_height

        self.feedback_text.setMinimumHeight(min_height)
        self.feedback_text.setMaximumHeight(max_height)
        self.feedback_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Show scrollbar when needed
        self.feedback_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.feedback_text.setPlaceholderText("Enter your next request or feedback here (Ctrl+Enter to submit) Supports pasting images")

        # Create a horizontal layout for buttons
        button_layout = QHBoxLayout()

        # Create the submit button
        submit_button = QPushButton("&Submit")
        submit_button.clicked.connect(self._submit_feedback)
        submit_button.setCursor(Qt.PointingHandCursor)  # Set mouse cursor to hand shape

        # Create the cancel button
        cancel_button = QPushButton("&Cancel")
        cancel_button.clicked.connect(self.close) # Connect cancel button to close the window
        cancel_button.setCursor(Qt.PointingHandCursor)  # Set mouse cursor to hand shape

        # Add buttons to the horizontal layout
        button_layout.addWidget(cancel_button) # Put cancel on the left
        button_layout.addWidget(submit_button) # Put submit on the right

        # Apply modern style and increase size for the submit button
        submit_button.setStyleSheet(
            "QPushButton {"
            "  padding: 10px 20px;margin-left:20px;"
            "  font-size: 14px;"
            "  border-radius: 5px;"
            "  background-color: #2196F3; /* Blue */"
            "  color: white;"
            "  border: none;"
            "}"
            "QPushButton:hover {"
            "  background-color: #1976D2;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #1565C0;"
            "}"
        )

        # Apply modern style and increase size for the cancel button
        cancel_button.setStyleSheet(
            "QPushButton {"
            "  padding: 10px 20px;margin-right:20px;"
            "  font-size: 14px;"
            "  border-radius: 5px;"
            "  background-color: #9E9E9E; /* Grey */"
            "  color: white;"
            "  border: none;"
            "}"
            "QPushButton:hover {"
            "  background-color: #757575;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #616161;"
            "}"
        )

        layout.addWidget(self.feedback_text)
        layout.addLayout(button_layout)
        # Add a line of text: by rowanyang center display, allow selection and copying of text
        if sys.platform == "darwin":  # macOS
            zoom_shortcut_text = "CMD+/-"
            line_height_shortcut_text = "CMD+Shift+L"
        else:  # Windows, Linux, etc.
            zoom_shortcut_text = "CTRL+/-"
            line_height_shortcut_text = "CTRL+ALT+H"

        label_text = f"Support {zoom_shortcut_text} to zoom font, {line_height_shortcut_text} to adjust line height (5 levels cycle)  Contact: RowanYang"
        by_rowanyang_label = QLabel(label_text)
        by_rowanyang_label.setStyleSheet(""" color: gray; font-size: 10pt; font-family:"PingFang SC", "Hiragino Sans GB", sans-serif; """)
        by_rowanyang_label.setTextInteractionFlags(Qt.TextSelectableByMouse) # Allow text selection

        # Create a QHBoxLayout to align "By RowanYang" to the center
        by_rowanyang_layout = QHBoxLayout()
        by_rowanyang_layout.addStretch(1)
        by_rowanyang_layout.addWidget(by_rowanyang_label)
        by_rowanyang_layout.addStretch(1)
        layout.addSpacing(10) # Add top margin for "By RowanYang" text layout
        layout.addLayout(by_rowanyang_layout)

    def _setup_shortcuts(self):
        """Set font scaling shortcuts"""
        # Zoom in font: Ctrl+=
        zoom_in = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in.activated.connect(lambda: self.adjust_font_size(1.1))

        # Zoom out font: Ctrl+-
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(lambda: self.adjust_font_size(0.9))

        # Reset font: Ctrl+0
        reset_font = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_font.activated.connect(self.reset_font_size)

        # Toggle line height: set different shortcuts based on platform
        if sys.platform == "darwin":  # macOS
            key_sequence = "Ctrl+Shift+L"  # On Mac, Ctrl maps to Command key, use simple combination
        else:  # Windows, Linux, etc.
            key_sequence = "Ctrl+Alt+H"

        toggle_line_height_shortcut = QShortcut(QKeySequence(key_sequence), self)
        toggle_line_height_shortcut.activated.connect(self._toggle_line_height)

    def _update_description_text(self):
        """Update description text area content and styles based on current settings"""
        # If text is passed from command line arguments, may need special handling
        prompt = self.prompt
        if isinstance(prompt, str) and prompt.startswith('"') and prompt.endswith('"'):
            # Remove quotes
            prompt = prompt[1:-1]

        try:
            # Try to detect and process Markdown
            is_markdown = self._is_markdown(prompt)

            # Log for debugging
            print(f"Detected text type: {'Markdown' if is_markdown else 'Plain text'}")

            if is_markdown:
                html_content = self._convert_markdown_to_html(prompt)
            else:
                html_content = self._convert_text_to_html(prompt)

            self.description_text.setHtml(html_content)

        except Exception as e:
            # If any error occurs, fall back to the most basic text display
            print(f"Error during text processing: {e}")

            # Try to directly convert escape characters to actual characters and set as plain text
            try:
                processed_text = self._preprocess_text(prompt)
                self.description_text.setPlainText(processed_text)
                print("Using plain text display (after preprocessing)")
            except:
                # Final fallback solution
                self.description_text.setPlainText(prompt)
                print("Using plain text display (original text)")

    def _toggle_line_height(self):
        """Cycle through line heights and update UI"""
        line_heights = [1.0, 1.1, 1.2, 1.3, 1.4]
        try:
            # Find current line height position in the list
            current_index = line_heights.index(self.line_height)
            next_index = (current_index + 1) % len(line_heights)
        except ValueError:
            # If current value is not in the preset list, start from default value 1.4
            next_index = 1  # Corresponds to 1.4

        self.line_height = line_heights[next_index]
        self._save_line_height(self.line_height)
        self._update_description_text()
        print(f"Line height switched to: {self.line_height}")

    def adjust_font_size(self, factor: float):
        """Adjust all font sizes proportionally"""
        app = QApplication.instance()
        current_font = app.font()
        new_size = max(8, int(current_font.pointSize() * factor))  # Minimum 8pt
        current_font.setPointSize(new_size)
        app.setFont(current_font)
        self._update_all_fonts()
        self._save_font_size(new_size)  # Save font size to settings

    def reset_font_size(self):
        """Reset to default font size"""
        app = QApplication.instance()
        default_font = app.font()
        default_size = 15  # Default font size
        default_font.setPointSize(default_size)
        app.setFont(default_font)
        self._update_all_fonts()
        self._save_font_size(default_size)  # Save reset font size

    def _save_font_size(self, size: int):
        """Save font size to settings"""
        self.settings.beginGroup("AppearanceSettings")
        self.settings.setValue("fontSize", size)
        self.settings.endGroup()

    def _load_font_size(self) -> int:
        """Load font size from settings, return default value if not found"""
        self.settings.beginGroup("AppearanceSettings")
        size = self.settings.value("fontSize", 15, type=int)  # Default 15pt
        self.settings.endGroup()
        return size

    def _save_line_height(self, line_height: float):
        """Save line height to settings"""
        self.settings.beginGroup("AppearanceSettings")
        self.settings.setValue("lineHeight", line_height)
        self.settings.endGroup()

    def _load_line_height(self) -> float:
        """Load line height from settings, return default value if not found"""
        self.settings.beginGroup("AppearanceSettings")
        line_height = self.settings.value("lineHeight", 1.3, type=float)
        self.settings.endGroup()
        return line_height

    def _update_all_fonts(self):
        """Update fonts for all controls in UI"""
        # Recursively update fonts for all child controls
        def update_widget_font(widget):
            widget.setFont(QApplication.font())

            # Special handling for checkbox icon size
            if isinstance(widget, QCheckBox):
                # Set icon size based on current font size
                font_size = QApplication.font().pointSize()
                icon_size = max(16, int(font_size * 1.2))  # Minimum 16px
                widget.setStyleSheet(f"""
                    QCheckBox::indicator {{
                        width: {icon_size}px;
                        height: {icon_size}px;
                    }}
                """)

            for child in widget.children():
                if isinstance(child, QWidget):
                    update_widget_font(child)

        update_widget_font(self)

    def showEvent(self, event):
        """Load saved font size when window is displayed"""
        super().showEvent(event)
        app = QApplication.instance()
        saved_size = self._load_font_size()
        current_font = app.font()
        current_font.setPointSize(saved_size)
        app.setFont(current_font)
        self._update_all_fonts()

    def _submit_feedback(self):
        feedback_text = self.feedback_text.toPlainText().strip()
        selected_options = []

        # Get selected predefined options if any
        if self.option_checkboxes:
            for i, checkbox in enumerate(self.option_checkboxes):
                if checkbox.isChecked():
                    selected_options.append(self.predefined_options[i])

        # Get Base64 image data
        image_data = self.feedback_text.get_image_data()

        # Combine selected options and feedback text
        final_feedback_parts = []

        # Add selected options
        if selected_options:
            final_feedback_parts.append("; ".join(selected_options))

        # Add user's text feedback
        if feedback_text:
            final_feedback_parts.append(feedback_text)

        # Join with a newline if both parts exist
        final_feedback = "\n\n".join(final_feedback_parts)
        images_b64 = [img['base64'] for img in image_data]

        self.feedback_result = FeedbackResult(
            interactive_feedback=final_feedback,
            images=images_b64
        )
        self.close()

    def closeEvent(self, event):
        # Save general UI settings for the main window (geometry, state)
        self.settings.beginGroup("MainWindow_General")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.endGroup()

        super().closeEvent(event)

    def run(self) -> FeedbackResult:
        self.show()
        QApplication.instance().exec()

        if not self.feedback_result:
            return FeedbackResult(interactive_feedback="")

        return self.feedback_result

    # Add method to handle image pasting
    def _on_image_pasted(self, pixmap):
        """Handle pasted images, display in image preview area"""
        # Ensure image container is visible
        if not self.images_container.isVisible():
            self.images_container.setVisible(True)
            self.scroll_area.setVisible(True)  # Also show scroll area
            # Only add elastic space when container is first displayed, ensure all images are left-aligned
            self.images_layout.addStretch(1)

        # Get original image dimensions
        original_width = pixmap.width()
        original_height = pixmap.height()

        # Fixed height, slightly reduce height to ensure complete display
        target_height = 80  # Further reduce image height to 40

        # Calculate scaled dimensions maintaining aspect ratio
        scaled_width = int(original_width * (target_height / original_height))

        # Create a container frame for placing image and delete button
        image_frame = QFrame()
        image_frame.setMinimumWidth(scaled_width)
        image_frame.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

        # Use QGridLayout with no spacing at all
        frame_layout = QGridLayout(image_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Create image label
        image_label = QLabel()
        image_label.setStyleSheet("border: none; background: transparent;")
        image_label.setScaledContents(False)
        image_label.setAlignment(Qt.AlignCenter)

        # Ensure image container has enough space but doesn't exceed
        image_label.setMinimumSize(scaled_width, target_height)
        image_label.setMaximumSize(scaled_width, target_height)

        # Scale image, maintain aspect ratio, ensure complete display (contain mode)
        scaled_pixmap = pixmap.scaled(
            scaled_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # Support retina screens
        device_pixel_ratio = QApplication.primaryScreen().devicePixelRatio()
        if device_pixel_ratio > 1.0:
            # For high DPI screens, create higher resolution pixmap
            hires_scaled_width = int(scaled_width * device_pixel_ratio)
            hires_target_height = int(target_height * device_pixel_ratio)

            hires_pixmap = pixmap.scaled(
                hires_scaled_width,
                hires_target_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Set device pixel ratio
            hires_pixmap.setDevicePixelRatio(device_pixel_ratio)
            image_label.setPixmap(hires_pixmap)
        else:
            image_label.setPixmap(scaled_pixmap)

        # Delete button, floating in top right corner
        delete_button = QPushButton("×")
        delete_button.setFixedSize(18, 18)
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 0, 0, 0.7);
                color: white;
                border-radius: 9px;
                font-weight: bold;
                border: none;
                padding-bottom: 2px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton:hover {
                background-color: red;
            }
        """)

        # Function to delete image
        def delete_image():
            # Get image index
            index = self.images_layout.indexOf(image_frame)
            if index >= 0:
                # Remove from layout
                widget = self.images_layout.itemAt(index).widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

                    # Delete from image data list
                    if index < len(self.feedback_text.image_data):
                        del self.feedback_text.image_data[index]

                    # Check if there are still images
                    has_images = False
                    for i in range(self.images_layout.count()):
                        item = self.images_layout.itemAt(i)
                        if item and not item.spacerItem() and item.widget():
                            has_images = True
                            break

                    # If no more images, hide container and scroll area
                    if not has_images:
                        self.images_container.setVisible(False)
                        self.scroll_area.setVisible(False)

        delete_button.clicked.connect(delete_image)

        # Add image and delete button to layout
        frame_layout.addWidget(image_label, 0, 0)
        frame_layout.addWidget(delete_button, 0, 0, Qt.AlignTop | Qt.AlignRight)

        # Add to image layout, ensure insertion before elastic space
        if self.images_layout.count() > 0:
            # Find elastic space index
            stretch_index = -1
            for i in range(self.images_layout.count()):
                if self.images_layout.itemAt(i).spacerItem():
                    stretch_index = i
                    break

            if stretch_index >= 0:
                # Insert image before elastic space
                self.images_layout.insertWidget(stretch_index, image_frame)
            else:
                # If no elastic space found, add directly to end
                self.images_layout.addWidget(image_frame)
        else:
            # If layout is empty, add image directly
            self.images_layout.addWidget(image_frame)

def feedback_ui(prompt: str, predefined_options: Optional[List[str]] = None, output_file: Optional[str] = None) -> Optional[FeedbackResult]:
    # ----- Enable high DPI scaling -----
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # Create QApplication or get existing instance
    app = QApplication.instance() or QApplication()
    app.setPalette(get_dark_mode_palette(app))
    app.setStyle("Fusion")

    # ----- Uniformly set global default font size -----
    default_font = app.font()           # Get current system/style default QFont
    default_font.setPointSize(15)       # Set global font size to 11pt, modify as needed
    app.setFont(default_font)

    ui = FeedbackUI(prompt, predefined_options)
    result = ui.run()

    if output_file and result:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        # Save the result to the output file
        with open(output_file, "w") as f:
            json.dump(result, f)
        return None

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run feedback UI")
    parser.add_argument("--prompt", default="I have completed the modifications according to your request.", help="Prompt message to display to user")
    parser.add_argument("--predefined-options", default="", help="JSON-encoded predefined options list")
    parser.add_argument("--output-file", help="JSON file path to save feedback results")
    args = parser.parse_args()

    # Parse JSON-encoded predefined options
    predefined_options = None
    if args.predefined_options:
        try:
            predefined_options = json.loads(args.predefined_options)
            if not isinstance(predefined_options, list):
                print(f"Warning: predefined_options is not a list, ignoring")
                predefined_options = None
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse predefined_options JSON: {e}")
            predefined_options = None

    result = feedback_ui(args.prompt, predefined_options, args.output_file)
    if result:
        print(f"\nReceived feedback:\n{result['interactive_feedback']}")
    sys.exit(0)