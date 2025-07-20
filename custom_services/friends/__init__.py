

import datetime
from fastapi import APIRouter

from utils.functions import paginate_data

from .schemas import FriendRequestAnswerRequest, FriendRequestAnswerResponse, FriendRequestDetail, FriendRequestRemoveRequest, FriendRequestRemoveResponse, FriendRequestStatus, FriendWithMessageOut, FriendsListRequest, FriendsListResponse, FriendsWithMessageRequest, FriendsWithMessageResponse, SendFriendRequest, SendFriendRequestResponse, UserPreview
from utils.dependencies import user_verify_dependency, psql_dependency
from utils.psql.models import FriendRequest, Message, User
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload, aliased
from utils.web_socket import WebSocketResponse, WebSocketTypes, websocket_manager
from sqlalchemy.sql import func, case

friends_router = APIRouter(prefix="/friends", tags=['Friends'])


@friends_router.post("/send_request", response_model=SendFriendRequestResponse)
async def send_friend_request(request: SendFriendRequest, user=user_verify_dependency, psql_db=psql_dependency):
    requester_email = user["email"]
    recipient_email = request.email

    requester_user = psql_db.query(User).where(User.email.__eq__(requester_email)).first()
    recipient_user = psql_db.query(User).where(User.email.__eq__(recipient_email)).first()

    if not requester_user or not recipient_user:
        return SendFriendRequestResponse(success=False, message="User is not available")
    
    # checking is friend request is already present or not
    is_friend_request_presents = psql_db.query(FriendRequest).where(
        or_(
            and_(
                FriendRequest.recipient_id.__eq__(recipient_user.id),
                FriendRequest.requester_id.__eq__(requester_user.id)
            ),
            and_(
                FriendRequest.recipient_id.__eq__(requester_user.id),
                FriendRequest.requester_id.__eq__(recipient_user.id)
            )
        )
    ).all()

    is_friend_request_present = is_friend_request_presents[0]

    # adding new friend request
    friend_request = is_friend_request_present or FriendRequest(
        requester_id=requester_user.id,
        recipient_id=recipient_user.id,
        status=FriendRequestStatus.PENDING.value
    )
    friend_request.requester_id=requester_user.id
    friend_request.recipient_id=recipient_user.id
    friend_request.status = FriendRequestStatus.PENDING.value
    psql_db.add(friend_request)

    # delete extra requests
    if len(is_friend_request_presents) > 1:
        for item in is_friend_request_presents[1:]:
            psql_db.delete(item)

    psql_db.commit()
    psql_db.refresh(friend_request)

    # send websocket message
    await websocket_manager.send_message(recipient_email, WebSocketResponse(
        type=WebSocketTypes.FRIEND_REQUEST_RECEIVED.value, 
        data={
            "message": f"Friend request received from {requester_email}"
        }
    ))
    await websocket_manager.send_message(requester_email, WebSocketResponse(
        type=WebSocketTypes.FRIEND_REQUEST_SENT.value,
        data={
            "message": f"Friend request sent to {recipient_email}"
        }
    ))

    return SendFriendRequestResponse(
        success=True,
        message="Friend request sent"
    )
    
    


@friends_router.post("/answer", response_model=FriendRequestAnswerResponse)
async def friend_request_answer(request: FriendRequestAnswerRequest, user=user_verify_dependency, psql_db=psql_dependency):
    requester_email = request.email
    recipient_email = user["email"]

    requester_user = psql_db.query(User).where(User.email.__eq__(requester_email)).first()
    recipient_user = psql_db.query(User).where(User.email.__eq__(recipient_email)).first()

    if not requester_user or not recipient_user:
        return FriendRequestAnswerResponse(success=False, message="User is not available")
    
    friend_request = psql_db.query(FriendRequest).where(
        and_(
            FriendRequest.recipient_id.__eq__(recipient_user.id),
            FriendRequest.requester_id.__eq__(requester_user.id),
        )
    ).first()

    if friend_request.status == request.status:
        return FriendRequestAnswerResponse(
            success=True,
            message=f"Friend request already {friend_request.status}"
        )
    
    # Update status
    friend_request.status = request.status.value
    friend_request.responded_at = datetime.datetime.now(datetime.timezone.utc)
    psql_db.add(friend_request)

    psql_db.commit()

    # send websocket message
    await websocket_manager.send_message(requester_email, WebSocketResponse(
        type=WebSocketTypes.FRIEND_REQUEST_ANSWER.value,
        data={
            "message": f"{recipient_email} has {request.status} the request"
        }
    ))
    await websocket_manager.send_message(recipient_email, WebSocketResponse(
        type=WebSocketTypes.FRIEND_REQUEST_ANSWER.value,
        data={
            "message": f"you have {request.status} the request from {requester_email}"
        }
    ))

    return FriendRequestAnswerResponse(
        success=True,
        message=f"Friend request {request.status}"
    )

@friends_router.post("/remove", response_model=FriendRequestRemoveResponse)
async def friend_request_remove(request: FriendRequestRemoveRequest, user=user_verify_dependency, psql_db=psql_dependency):
    email1 = user["email"]
    email2 = request.email

    user1 = psql_db.query(User).where(User.email.__eq__(email1)).first()
    user2 = psql_db.query(User).where(User.email.__eq__(email2)).first()

    if not user1 or not user2:
        return FriendRequestAnswerResponse(success=False, message="User is not available")
    
    friend_request = psql_db.query(FriendRequest).where(
        or_(
            and_(
                FriendRequest.recipient_id.__eq__(user1.id),
                FriendRequest.requester_id.__eq__(user2.id),
            ),
            and_(
                FriendRequest.recipient_id.__eq__(user2.id),
                FriendRequest.requester_id.__eq__(user1.id),
            )
        )
    ).all()

    if len(friend_request) == 0:
        return FriendRequestRemoveResponse(success=False, message="No request found")
    friend_request[0].status = FriendRequestStatus.REMOVED.value
    psql_db.add(friend_request[0])
    psql_db.commit()

    await websocket_manager.send_message(email1, WebSocketResponse(
        type=WebSocketTypes.FRIEND_REQUEST_REMOVED,
        data={
            "message": f"Friend request with {email2} is removed"
        }
    ))
    await websocket_manager.send_message(email2, WebSocketResponse(
        type=WebSocketTypes.FRIEND_REQUEST_REMOVED,
        data={
            "message": f"Friend request with {email1} is removed"
        }
    ))

    return FriendRequestRemoveResponse(
        success=True,
        message="Friend request removed"
    )


@friends_router.post("/list", response_model=FriendsListResponse)
async def get_friend_requests(request: FriendsListRequest, user=user_verify_dependency, psql_db=psql_dependency):
    user_record = psql_db.query(User).where(User.email.__eq__(user["email"])).first()
    status = [item.value for item in request.status]
    friend_requests = psql_db.query(FriendRequest).where(
        and_(
            FriendRequest.status.in_(status),
            or_(
                FriendRequest.recipient_id.__eq__(user_record.id),
                FriendRequest.requester_id.__eq__(user_record.id)
            )
        )
    ).options(
        joinedload(FriendRequest.requester), 
        joinedload(FriendRequest.recipient)
    ).order_by(FriendRequest.updated_at.desc())

    data, next_offset, total = paginate_data(friend_requests, request.limit, request.offset)

    return FriendsListResponse(
        data=[
            FriendRequestDetail(
                status=fr.status,
                created_at=fr.created_at,
                updated_at=fr.updated_at,
                responded_at=fr.responded_at,
                requester=UserPreview(
                    email=fr.requester.email,
                    display_name=fr.requester.display_name,
                    phone=fr.requester.phone
                ),
                recipient=UserPreview(
                    email=fr.recipient.email,
                    display_name=fr.recipient.display_name,
                    phone=fr.recipient.phone
                )
            )
            for fr in data
        ],
        next_offset=next_offset,
        total=total
    )


@friends_router.post("/friends_with_last_message", response_model=FriendsWithMessageResponse)
async def get_friends_with_last_message(request: FriendsWithMessageRequest, user_data=user_verify_dependency, psql_db=psql_dependency):
    current_user_id = psql_db.query(User.id).filter(User.email == user_data["email"]).scalar()

    q = request.q or ""
    limit = request.limit
    offset = request.offset

    # Aliases
    other_user = aliased(User)
    friend_request = aliased(FriendRequest)

    # Subquery: Get latest message timestamp per friend pair
    message_time_subq = (
        psql_db.query(
            func.max(Message.updated_at).label("last_message_time"),
            case(
                (Message.sender_id == current_user_id, Message.recipient_user_id)
            , else_=Message.sender_id).label("other_user_id")
        )
        .filter(
            or_(
                and_(Message.sender_id == current_user_id, Message.recipient_user_id != None),
                and_(Message.recipient_user_id == current_user_id, Message.sender_id != None)
            )
        )
        .group_by("other_user_id")
        .subquery()
    )

    # Subquery: Get the actual latest message
    latest_message_subq = (
        psql_db.query(Message)
        .join(
            message_time_subq,
            and_(
                or_(
                    and_(Message.sender_id == current_user_id, Message.recipient_user_id == message_time_subq.c.other_user_id),
                    and_(Message.recipient_user_id == current_user_id, Message.sender_id == message_time_subq.c.other_user_id)
                ),
                Message.updated_at == message_time_subq.c.last_message_time
            )
        )
        .subquery()
    )

    latest_message_alias = aliased(Message, latest_message_subq)

    # Main query
    query = (
        psql_db.query(
            other_user,
            friend_request.updated_at.label("friend_request_updated_at"),
            latest_message_alias.text.label("last_message_text"),
            latest_message_alias.updated_at.label("last_message_updated_at")
        )
        .join(
            friend_request,
            or_(
                and_(friend_request.requester_id == current_user_id, friend_request.recipient_id == other_user.id),
                and_(friend_request.recipient_id == current_user_id, friend_request.requester_id == other_user.id),
            )
        )
        .outerjoin(
            latest_message_alias,
            or_(
                and_(latest_message_alias.sender_id == current_user_id, latest_message_alias.recipient_user_id == other_user.id),
                and_(latest_message_alias.recipient_user_id == current_user_id, latest_message_alias.sender_id == other_user.id),
            )
        )
        .filter(friend_request.status == FriendRequestStatus.ACCEPTED.value)
    )

    # 🔍 Search filter (on email, display_name, message text)
    if q:
        query = query.filter(
            or_(
                other_user.email.ilike(f"%{q}%"),
                other_user.display_name.ilike(f"%{q}%"),
                latest_message_alias.text.ilike(f"%{q}%")
            )
        )

    # 📥 Sort by latest message or friend request
    query = query.order_by(desc(func.coalesce(latest_message_alias.updated_at, friend_request.updated_at)))

    # 📊 Pagination
    paginated_data, next_offset, total = paginate_data(query, limit, offset)

    return FriendsWithMessageResponse(
        data=[
            FriendWithMessageOut(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                friend_since=friend_request_updated_at,
                last_message=last_message_text,
                last_activity_time=last_message_updated_at or friend_request_updated_at
            )
            for user, friend_request_updated_at, last_message_text, last_message_updated_at in paginated_data
        ],
        next_offset=next_offset,
        total=total
    )
