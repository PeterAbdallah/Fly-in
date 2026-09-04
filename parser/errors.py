class ParseError(Exception):
    """Raised when the map file is malformed."""

    def __init__(self, line_num: int, message: str) -> None:
        self.line_num = line_num
        self.message = message
        super.__init__(f"Line {line_num}: {message}")
