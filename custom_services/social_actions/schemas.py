

from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from custom_services.friends.schemas import FriendRequestStatus
from utils.models import PaginatedRequestModel, PaginatedResponseModel


class UserOut(BaseModel):
    email: str
    display_name: str
    phone: Optional[str]
    friend_status: FriendRequestStatus | None

    model_config = ConfigDict(from_attributes=True)

class SearchUsersRequest(PaginatedRequestModel):
    q: Optional[str | None]

class SearchUsersResponse(PaginatedResponseModel[UserOut]):
    pass
