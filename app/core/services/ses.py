from typing import Protocol

from app.core.schemas import EmailMessage


class EmailSender(Protocol):
    async def send_email(self, msg: EmailMessage) -> None: ...


class SesEmailSenderService:
    def __init__(self) -> None: ...

    async def send_email(self, msg: EmailMessage, send_as_html: bool = True) -> None: ...
