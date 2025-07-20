

from typing import Optional
from pydantic import BaseModel

from custom_services.friends.schemas import FriendRequestStatus
from custom_services.social_actions.schemas import UserOut
from utils.models import BaseResponseModel, PaginatedRequestModel, PaginatedResponseModel
from utils.psql.models import User


class GetLoginTokenRequest(BaseModel):
    email: str

class GetLoginTokenResponse(BaseModel):
    token: str


class AdminUserModel(BaseModel):
    email: str
    display_name: str
    phone: Optional[str]

class GetAllUsersRequest(PaginatedRequestModel):
    q: Optional[str | None]

class GetAllUsersResponse(PaginatedResponseModel[AdminUserModel]):
    pass


class FriendRequestUser(BaseModel):
    email: str
    display_name: str

class FriendRequestModel(BaseModel):
    requester: FriendRequestUser
    recipient: FriendRequestUser
    status: FriendRequestStatus

class GetFriendsRequest(PaginatedRequestModel):
    q: Optional[str | None]
    email: str

class GetFriendsResponse(PaginatedResponseModel[FriendRequestModel]):
    pass


class GetContextUsersRequest(PaginatedRequestModel):
    q: Optional[str | None]
    context_email: str

class GetContextUsersResponse(PaginatedResponseModel[UserOut]):
    pass


class SetFriendRequestRequest(BaseModel):
    requester_email: str
    recipient_email: str
    status: FriendRequestStatus

class SetFriendRequestResponse(BaseResponseModel):
    pass


class MessageUser(BaseModel):
    email: str
    display_name: str

class MessageModel(BaseModel):
    sender: MessageUser
    recipient: MessageUser
    text: str

class GetMessagesRequest(PaginatedRequestModel):
    sender_email: str
    recipient_email: str | None

class GetMessagesResponse(PaginatedResponseModel[MessageModel]):
    pass