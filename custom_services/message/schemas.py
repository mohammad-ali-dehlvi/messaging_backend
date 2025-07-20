from typing import Optional
from pydantic import BaseModel

from utils.models import BaseResponseModel, PaginatedRequestModel, PaginatedResponseModel

class Recipient(BaseModel):
    email: str

class Sender(BaseModel):
    email: str

class MessageModel(BaseModel):
    text: str
    recipient: Recipient
    sender: Sender

class MessageGetRequest(PaginatedRequestModel):
    email: str
    q: Optional[str | None]

class MessageGetResponse(PaginatedResponseModel[MessageModel]):
    pass


class SendMessageRequest(BaseModel):
    email: str
    text: str

class SendMessageResponse(BaseResponseModel):
    pass
