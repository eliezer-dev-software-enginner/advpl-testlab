import os
import re
import sys
from pathlib import Path


_LINE_NUMBER = re.compile(r"\b(?:na )?linha\s+(\d+)\b", re.IGNORECASE)
_RED = "\033[31;1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


class SourceValidationError(Exception):
    def __init__(self, source_path, source, original):
        self.source_path = Path(source_path)
        self.original = original
        self.original_message = str(original)
        match = _LINE_NUMBER.search(self.original_message)
        line = int(match.group(1)) if match else None
        if line is not None and "TokenType.NEWLINE" in self.original_message:
            line = max(1, line - 1)
        self.line = line
        source_lines = source.splitlines()
        self.source_line = (
            source_lines[line - 1] if line and line <= len(source_lines) else ""
        )
        if "TokenType.NEWLINE" in self.original_message:
            self.column = len(self.source_line.rstrip()) + 1
        else:
            self.column = len(self.source_line) - len(self.source_line.lstrip()) + 1
        message = _LINE_NUMBER.sub("", self.original_message).strip()
        message = re.sub(r"\s+", " ", message)
        super().__init__(message)


def supports_color(stream):
    return os.environ.get("NO_COLOR") is None and bool(
        getattr(stream, "isatty", lambda: False)()
    )


def format_diagnostic(error, color=False):
    if isinstance(error, SourceValidationError):
        label = "SyntaxError"
        location = str(error.source_path)
        if error.line is not None:
            location += f":{error.line}:{error.column}"
        excerpt = ""
        if error.source_line:
            gutter = str(error.line)
            displayed_line = error.source_line.rstrip().expandtabs(4)
            displayed_column = len(
                error.source_line[: error.column - 1].expandtabs(4)
            )
            excerpt = (
                f"\n  {gutter} | {displayed_line}"
                f"\n  {' ' * len(gutter)} | {' ' * displayed_column}^"
            )
        message = f"{label}: {error}{excerpt}\n  --> {location}"
    else:
        label = type(error).__name__
        message = f"{label}: {error}"

    if color:
        if "\n  --> " in message:
            body, location = message.rsplit("\n  --> ", 1)
            return f"{_RED}{body}{_RESET}\n{_DIM}  --> {location}{_RESET}"
        return f"{_RED}{message}{_RESET}"
    return message


def print_diagnostic(error, stream=None):
    stream = stream or sys.stderr
    print(format_diagnostic(error, color=supports_color(stream)), file=stream)
