"""Database-zone errors: lookup misses stay honest (grounded-data rule)."""


class RecordNotFoundError(Exception):
    """A lookup id does not exist in the store (course/degree/plan/session).

    Maps to HTTP 404 via the server layer — never fabricated filler.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message