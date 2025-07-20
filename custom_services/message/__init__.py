

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from utils.psql.models import User, Message
from utils.web_socket import WebSocketResponse, WebSocketTypes, websocket_manager
from .schemas import MessageGetRequest, MessageGetResponse, MessageModel, Recipient, SendMessageRequest, SendMessageResponse, Sender
from utils.dependencies import user_verify_dependency, psql_dependency

message_router = APIRouter(prefix="/messaging", tags=["Messaging"])

@message_router.post("/message_get", response_model=MessageGetResponse)
async def message_get(request: MessageGetRequest, user=user_verify_dependency, psql_db=psql_dependency):
    user1_email: str = user["email"]
    user2_email: str = request.email
    q = request.q
    limit = request.limit
    offset = request.offset

    user1 = psql_db.query(User).filter(User.email == user1_email).first()
    user2 = psql_db.query(User).filter(User.email == user2_email).first()

    not_found_user = user1_email if not user1 else user2_email if not user2 else None
    if not_found_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{not_found_user} not found"
        )

    # Base query for messages between user1 and user2
    base_query = psql_db.query(Message).filter(
        or_(
            and_(Message.sender_id == user1.id, Message.recipient_user_id == user2.id),
            and_(Message.sender_id == user2.id, Message.recipient_user_id == user1.id),
        )
    ).options(
        joinedload(Message.sender),
        joinedload(Message.recipient_user),
    )

    # Optional full-text search (case-insensitive, partial match)
    if q:
        base_query = base_query.filter(Message.text.ilike(f"%{q}%"))

    total = base_query.count()

    messages = base_query.order_by(Message.created_at.asc()) \
        .offset(offset).limit(limit).all()

    message_models = [
        MessageModel(
            text=msg.text,
            sender=Sender(email=msg.sender.email),
            recipient=Recipient(email=msg.recipient_user.email),
        )
        for msg in messages
    ]

    next_offset = offset + limit if offset + limit < total else None

    return MessageGetResponse(
        data=message_models,
        next_offset=next_offset,
        total=total
    )


@message_router.post("/send_message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest, psql_db=psql_dependency, user=user_verify_dependency):
    sender_email = user["email"]
    recipient_email = request.email

    sender_user = psql_db.query(User).where(User.email.__eq__(sender_email)).first()
    recipient_user = psql_db.query(User).where(User.email.__eq__(recipient_email)).first()

    if not sender_user or not recipient_user:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    sender_id = sender_user.id
    recipient_id = recipient_user.id

    message = Message(
        text=request.text,
        sender_id=sender_id,
        recipient_user_id=recipient_id
    )

    psql_db.add(message)
    psql_db.commit()
    psql_db.refresh(message)

    message = psql_db.query(Message).where(
        Message.id.__eq__(message.id)
    ).options(
        joinedload(Message.sender), 
        joinedload(Message.recipient_user)
    ).first()

    message_model = MessageModel(
            text=message.text,
            sender=Sender(email=message.sender.email),
            recipient=Recipient(email=message.recipient_user.email),
        )

    await websocket_manager.send_message(recipient_email, WebSocketResponse(type=WebSocketTypes.MESSAGE_RECEIVED.value, data=message_model.model_dump()))
    await websocket_manager.send_message(sender_email, WebSocketResponse(type=WebSocketTypes.MESSAGE_SENT.value, data=message_model.model_dump()))

    return SendMessageResponse(
        success=True,
        message="Message sent"
    )
