class ParseError(Exception):
    """Raised when the map file is malformed."""

    def __init__(self, line_num: int, message: str) -> None:
        self.line_num = line_num
        self.message = message
        super().__init__(f"Line {line_num}: {message}")


class DuplicateZoneError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Duplicate zone name: {name}")
        # This will be the message in the ParseError


class DuplicateStartError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Duplicate start zone: {name}")
        # This will be the message in the ParseError


class DuplicateEndError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Duplicate end zone: {name}")
        # This will be the message in the ParseError


class NonExistingZoneError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Zone '{name}' doesn't exist")
