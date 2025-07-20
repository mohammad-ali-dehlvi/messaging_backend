from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from custom_services.social_actions import social_actions_router
from custom_services.auth import auth_router
from custom_services.web_socket import web_socket_router
from custom_services.friends import friends_router
from custom_services.message import message_router
from custom_services.admin import admin_router
import firebase_admin
from dotenv import load_dotenv
import os

load_dotenv()

config = {
    "type": os.getenv("TYPE"),
    "project_id": os.getenv("PROJECT_ID"),
    "private_key_id": os.getenv("PRIVATE_KEY_ID"),
    "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("CLIENT_EMAIL"),
    "client_id": os.getenv("CLIENT_ID"),
    "auth_uri": os.getenv("AUTH_URI"),
    "token_uri": os.getenv("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("UNIVERSE_DOMAIN")
}

cred_obj = firebase_admin.credentials.Certificate(config)
default_app = firebase_admin.initialize_app(credential=cred_obj)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router)
app.include_router(web_socket_router)
app.include_router(social_actions_router)
app.include_router(friends_router)
app.include_router(message_router)
app.include_router(admin_router)