from fastapi import APIRouter, HTTPException
from .schemas import SearchUsersRequest, SearchUsersResponse, UserOut
from utils.dependencies import user_verify_dependency,psql_dependency
from utils.psql.models import FriendRequest, User
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from utils.functions import paginate_data

social_actions_router = APIRouter(prefix="/social_actions", tags=["SocialActions"])

@social_actions_router.post("/search_users", response_model=SearchUsersResponse)
async def search_users(request: SearchUsersRequest, user_data=user_verify_dependency, psql_db=psql_dependency):
    q = request.q or ""
    limit = request.limit
    offset = request.offset
    email = user_data["email"]

    current_user: User = psql_db.query(User).filter(User.email == email).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Aliased FriendRequest to allow outer join in both directions
    FriendRequestAlias = aliased(FriendRequest)

    # Join FriendRequest (in either direction) to get status if exists
    users_query = (
        psql_db.query(User, FriendRequestAlias.status.label("friend_status"))
        .outerjoin(
            FriendRequestAlias,
            or_(
                and_(
                    FriendRequestAlias.requester_id == current_user.id,
                    FriendRequestAlias.recipient_id == User.id,
                ),
                and_(
                    FriendRequestAlias.recipient_id == current_user.id,
                    FriendRequestAlias.requester_id == User.id,
                ),
            ),
        )
        .filter(User.id != current_user.id)
    )

    if q:
        users_query = users_query.filter(
            or_(
                User.email.ilike(f"%{q}%"),
                User.display_name.ilike(f"%{q}%"),
            )
        )

    users_query = users_query.order_by(User.email.asc())

    users_data, next_offset, total = paginate_data(users_query, limit, offset)

    return SearchUsersResponse(
        data=[
            UserOut(**user.__dict__, friend_status=friend_status)  # Add friend_status to your model
            for user, friend_status in users_data
        ],
        next_offset=next_offset,
        total=total
    )
    