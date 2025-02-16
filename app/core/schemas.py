from pydantic import BaseModel, EmailStr, Field


class EmailMessage(BaseModel):
    target_email: EmailStr
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
