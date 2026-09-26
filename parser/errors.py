class ParseError(Exception):
    """Raised when the map file is malformed."""

    def __init__(self, line_num: int, message: str) -> None:
        """Initialize the error with the offending line and a message.

        Args:
            line_num: The line number in the input file where the error occurred.
            message: A human-readable description of what went wrong.
        """
        self.line_num = line_num
        self.message = message
        super().__init__(f"Line {line_num}: {message}")


class MapError(Exception):
    """Base for semantic errors raised while building the graph.
    Parser catches this and re-raises as ParseError with the line number."""
    pass

class DuplicateZoneError(MapError):
    """Raised when a zone name is defined more than once."""

    def __init__(self, zoneName: str) -> None:
        """Initialize the error with the duplicated zone name.

        Args:
            zoneName: The name of the zone that was already defined.
        """
        self.zoneName = zoneName
        super().__init__(f"Duplicate zone name: {zoneName}")
        # This will be the message in the ParseError


class DuplicateStartError(MapError):
    """Raised when more than one start zone is defined."""

    def __init__(self, zoneName: str) -> None:
        """Initialize the error with the extra start zone's name.

        Args:
            zoneName: The name of the zone that attempted to become
                a second start zone.
        """
        self.zoneName = zoneName
        super().__init__(f"Duplicate start zone: {zoneName}")
        # This will be the message in the ParseError


class DuplicateEndError(MapError):
    """Raised when more than one end zone is defined."""

    def __init__(self, zoneName: str) -> None:
        """Initialize the error with the extra end zone's name.

        Args:
            zoneName: The name of the zone that attempted to become
                a second end zone.
        """
        self.zoneName = zoneName
        super().__init__(f"Duplicate end zone: {zoneName}")
        # This will be the message in the ParseError


class NonExistingZoneError(MapError):
    """Raised when a connection references a zone that was never defined."""

    def __init__(self, zoneName: str) -> None:
        """Initialize the error with the missing zone's name.

        Args:
            zoneName: The name of the zone that could not be found.
        """
        self.zoneName = zoneName
        super().__init__(f"Zone '{zoneName}' doesn't exist")


class SameZoneConnectionError(MapError):
    """Raised when a connection links a zone to itself."""

    def __init__(self) -> None:
        """Initialize the error with a fixed, descriptive message."""
        super().__init__(f"A zone cannot be connected to itself!")