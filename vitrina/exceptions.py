from rest_framework.exceptions import APIException


class UAPIException(APIException):
    def __init__(
        self,
        code: str,
        type: str,
        template: str,
        message: str,
        context: dict | None = None,
        status_code: int = 400,
    ) -> None:
        self.detail = {
            "code": code,
            "type": type,
            "template": template,
            "message": message,
            "context": context,
            "additionalProperties": None,
        }
        self.status_code = status_code
