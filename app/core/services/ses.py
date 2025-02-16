from typing import Protocol

from app.core.schemas import EmailMessage


class EmailSender(Protocol):
    async def send_email(self, msg: EmailMessage): ...


class SesEmailSenderService:
    def __init__(self): ...

    async def send_email(self, msg: EmailMessage, send_as_html: bool = True): ...
