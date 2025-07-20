from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, aliased
from firebase_admin import auth

from custom_services.social_actions.schemas import UserOut
from utils.functions import paginate_data

from .schemas import AdminUserModel, FriendRequestModel, FriendRequestUser, GetAllUsersRequest, GetAllUsersResponse, GetContextUsersRequest, GetContextUsersResponse, GetFriendsRequest, GetFriendsResponse, GetLoginTokenRequest, GetLoginTokenResponse, GetMessagesRequest, GetMessagesResponse, MessageModel, MessageUser, SetFriendRequestRequest, SetFriendRequestResponse
from .utils import check_admin_user
from utils.dependencies import user_verify_dependency, psql_dependency, firestore_dependency
from utils.psql.models import FriendRequest, User, Message

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.post("/get_login_token", response_model=GetLoginTokenResponse)
async def get_login_token(request: GetLoginTokenRequest, admin_user=user_verify_dependency):
    check_admin_user(admin_user['email'])

    email = request.email
    
    user: auth.UserRecord = auth.get_user_by_email(email)

    if not user:
        return HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    token_bytes: bytes = auth.create_custom_token(user.uid)

    return GetLoginTokenResponse(
        token=token_bytes.decode("utf-8")
    )


@admin_router.post("/get_all_users", response_model=GetAllUsersResponse)
async def get_all_users(request: GetAllUsersRequest, user=user_verify_dependency, psql_db=psql_dependency):
    check_admin_user(user["email"])

    q = request.q
    limit = request.limit
    offset = request.offset

    users_query = psql_db.query(User)

    if q:
        users_query = users_query.where(
            or_(
                User.email.ilike(f"%{q}%"),
                User.display_name.ilike(f"%{q}%")
            )
        )

    total = users_query.count()

    users_query = users_query.offset(offset).limit(limit)

    users = users_query.all()

    next_offset = offset + limit if offset + limit < total else None

    return GetAllUsersResponse(
        data=[
            AdminUserModel(**user.__dict__)    
            for user in users
        ],
        next_offset=next_offset,
        total=total
    )

@admin_router.post("/get_friends", response_model=GetFriendsResponse)
async def get_friends(request: GetFriendsRequest, admin_user=user_verify_dependency, psql_db=psql_dependency):
    check_admin_user(admin_user["email"])

    email=request.email
    q=request.q
    limit=request.limit
    offset=request.offset

    user = psql_db.query(User).where(User.email.__eq__(email)).first()

    if not user:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = user.id

    query = psql_db.query(FriendRequest).where(
        or_(
            FriendRequest.recipient_id.__eq__(user_id),
            FriendRequest.requester_id.__eq__(user_id)
        )
    ).options(
        joinedload(FriendRequest.recipient),
        joinedload(FriendRequest.requester)
    )

    if q:
        ilike_pattern = f"%{q}%"
        query = query.filter(
            or_(
                FriendRequest.recipient.has(
                    or_(
                        User.email.ilike(ilike_pattern),
                        User.display_name.ilike(ilike_pattern),
                    )
                ),
                FriendRequest.requester.has(
                    or_(
                        User.email.ilike(ilike_pattern),
                        User.display_name.ilike(ilike_pattern),
                    )
                ),
            )
        )

    data, next_offset, total = paginate_data(query, limit, offset)

    return GetFriendsResponse(
        data=[
            FriendRequestModel(
                recipient=FriendRequestUser(
                    email=item.recipient.email,
                    display_name=item.recipient.display_name
                ),
                requester=FriendRequestUser(
                    email=item.requester.email,
                    display_name=item.requester.display_name
                ),
                status=item.status
            )
            for item in data
        ],
        next_offset=next_offset,
        total=total
    )


@admin_router.post("/search_context_users", response_model=GetContextUsersResponse)
async def search_context_users(request: GetContextUsersRequest, admin_user=user_verify_dependency, psql_db=psql_dependency):
    check_admin_user(admin_user["user"])

    email = request.context_email
    q = request.q
    limit = request.limit
    offset = request.offset

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

    return GetContextUsersResponse(
        data=[
            UserOut(**user.__dict__, friend_status=friend_status)
            for user, friend_status in users_data
        ],
        next_offset=next_offset,
        total=total
    )



@admin_router.post("/set_friend_request" ,response_model=SetFriendRequestResponse)
async def set_friend_request(request: SetFriendRequestRequest, admin_user=user_verify_dependency, psql_db=psql_dependency):
    check_admin_user(admin_user["email"])

    requester_email = request.requester_email
    recipient_email = request.recipient_email
    friend_status = request.status

    requester = psql_db.query(User).where(User.email.__eq__(requester_email)).first()
    recipient = psql_db.query(User).where(User.email.__eq__(recipient_email)).first()

    if not requester or not recipient:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    requester_id = requester.id
    recipient_id = recipient.id

    friend_request = psql_db.query(FriendRequest).where(
        or_(
            and_(
                FriendRequest.recipient_id.__eq__(recipient_id),
                FriendRequest.requester_id.__eq__(requester_id)
            ),
            and_(
                FriendRequest.recipient_id.__eq__(requester_id),
                FriendRequest.requester_id.__eq__(recipient_id)
            )
        )
    ).first()

    if not friend_request:
        friend_request = FriendRequest(
            recipient_id=recipient_id,
            requester_id=requester_id
        )
    
    friend_request.status = friend_status

    psql_db.add(friend_request)
    psql_db.commit()
    psql_db.refresh(friend_request)

    return SetFriendRequestResponse(
        success=True,
        message="Friend request added"
    )


@admin_router.post("/get_messages", response_model=GetMessagesResponse)
async def get_messages(request: GetMessagesRequest, admin_user=user_verify_dependency, psql_db=psql_dependency):
    check_admin_user(admin_user["email"])

    sender_email = request.sender_email
    recipient_email = request.recipient_email
    limit = request.limit
    offset = request.offset

    sender = psql_db.query(User).where(User.email.__eq__(sender_email)).first()
    recipient = psql_db.query(User).where(User.email.__eq__(recipient_email)).first() if recipient_email else None

    if not sender:
        return HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail="Sender user not found"
        )
    
    sender_id = sender.id
    recipient_id = recipient.id if recipient else None

    id_query = Message.sender_id.__eq__(sender_id) if not recipient_id else and_(
        Message.sender_id.__eq__(sender_id),
        Message.recipient_user_id.__eq__(recipient_id)
    )
    
    query = psql_db.query(Message).where(id_query).options(
        joinedload(Message.sender),
        joinedload(Message.recipient_user)
    )

    data, next_offset, total = paginate_data(query, limit, offset)

    return GetMessagesResponse(
        data=[
            MessageModel(
                text=item.text,
                sender=MessageUser(
                    email=item.sender.email,
                    display_name=item.sender.display_name
                ),
                recipient=MessageUser(
                    email=item.recipient_user.email,
                    display_name=item.recipient_user.display_name
                )
            )
            for item in data
        ],
        next_offset=next_offset,
        total=total
    )
