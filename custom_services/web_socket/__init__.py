

from fastapi import HTTPException, WebSocket, APIRouter, WebSocketDisconnect, status
from firebase_admin import auth
from utils.web_socket import websocket_manager
from utils.dependencies import user_verify_dependency

web_socket_router = APIRouter(tags=["WebSocket"])

@web_socket_router.websocket("/message")
async def message_socket(websocket: WebSocket, token: str):
    try:
        user = auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_id = user["uid"]
    await websocket.accept()
    try:
        websocket_manager.connect(user_id, websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(user_id)

@web_socket_router.get("/test_socket")
async def test_socket(user=user_verify_dependency):
    websocket_manager.send_message(user["email"], user)

    return {"message": "Message sent"}