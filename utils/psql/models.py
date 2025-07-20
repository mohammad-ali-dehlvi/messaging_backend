from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey, CheckConstraint, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base

Base = declarative_base()

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str]
    phone: Mapped[Optional[str]]

    sent_requests = relationship("FriendRequest", back_populates="requester", foreign_keys="FriendRequest.requester_id")
    received_requests = relationship("FriendRequest", back_populates="recipient", foreign_keys="FriendRequest.recipient_id")


class FriendRequest(Base, TimestampMixin):
    __tablename__ = "friend_requests"
    __table_args__ = (
        UniqueConstraint("requester_id", "recipient_id"),
        CheckConstraint("requester_id <> recipient_id", name="no_self_request")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(default="pending")  # 'pending', 'accepted', 'rejected', 'removed'
    responded_at: Mapped[Optional[datetime]]

    requester = relationship("User", back_populates="sent_requests", foreign_keys=[requester_id])
    recipient = relationship("User", back_populates="received_requests", foreign_keys=[recipient_id])


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    members = relationship("GroupMember", back_populates="group")


class GroupMember(Base, TimestampMixin):
    __tablename__ = "group_members"
    __table_args__ = (
        PrimaryKeyConstraint("group_id", "user_id"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_admin: Mapped[bool] = mapped_column(default=False)

    group = relationship("Group", back_populates="members")
    user = relationship("User")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "(recipient_user_id IS NOT NULL AND recipient_group_id IS NULL) OR "
            "(recipient_user_id IS NULL AND recipient_group_id IS NOT NULL)",
            name="check_single_recipient"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipient_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipient_group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    text: Mapped[Optional[str]]

    sender = relationship("User", foreign_keys=[sender_id])
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    attachments = relationship("MessageAttachment", back_populates="message")


class MessageAttachment(Base, TimestampMixin):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    file_url: Mapped[str]
    file_type: Mapped[str] = mapped_column(CheckConstraint("file_type IN ('file', 'audio')"))

    message = relationship("Message", back_populates="attachments")
