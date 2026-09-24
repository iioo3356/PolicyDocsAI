class ApplicationError(Exception):
    """Transport-independent failure translated by the HTTP boundary."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
