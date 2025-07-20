from enum import Enum
from fastapi import WebSocket
from firebase_admin import firestore, auth
from pydantic import BaseModel

class WebSocketTypes(Enum):
    FRIEND_REQUEST_REMOVED="FRIEND_REQUEST_REMOVED"
    FRIEND_REQUEST_SENT="FRIEND_REQUEST_SENT"
    FRIEND_REQUEST_RECEIVED="FRIEND_REQUEST_RECEIVED"
    FRIEND_REQUEST_ANSWER="FRIEND_REQUEST_ANSWER"
    MESSAGE_RECEIVED="MESSAGE_RECEIVED"
    MESSAGE_SENT="MESSAGE_SENT"

class WebSocketResponse(BaseModel):
    type: str
    data: dict

class WebSocketManager:
    email_to_id: dict[str, str] = {}
    connections: dict[str, WebSocket] = {}
    def __init__(self):
        self.connections = {}

    def connect(self, user_id: str, websocket: WebSocket):
        self.connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if  user_id in self.connections:
            del self.connections[user_id]

    def get_id_from_email(self, email: str):
        if email in self.email_to_id:
            return self.email_to_id[email]
        try:
            user: auth.UserRecord = auth.get_user_by_email(email)
            uid: str = user.uid
            self.email_to_id[email] = uid
            return uid
        except:
            return None
        
    async def send_message_to_user_id(self, user_id: str, data: WebSocketResponse):
        if user_id in self.connections:
            web_socket = self.connections[user_id]
            await web_socket.send_json(data.__dict__)
    
    async def send_message(self, user_email: str, data: WebSocketResponse):
        uid = self.get_id_from_email(user_email)
        if uid:
            await self.send_message_to_user_id(uid, data)
        

websocket_manager = WebSocketManager()
