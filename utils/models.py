

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field


class BaseResponseModel(BaseModel):
    success: bool = Field(description="True if API is runs without any error")
    message: Optional[str] = Field(description="Message related to API's success and failure")


class PaginatedRequestModel(BaseModel):
    limit: int
    offset: int

T = TypeVar('T')
class PaginatedResponseModel(BaseModel, Generic[T]):
    data: List[T]
    next_offset: int | None
    total: int
