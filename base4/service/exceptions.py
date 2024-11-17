from fastapi.exceptions import HTTPException


class ServiceException(BaseException):
    def __init__(self, error_code: str, message: str, status_code: int = 400, additional_info: dict = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.additional_info = additional_info if additional_info is not None else {}

        super().__init__(message)

    def make_http_exception(self) -> HTTPException:
        return HTTPException(self.status_code, detail={'code': self.error_code, 'message': self.message, **self.additional_info})
