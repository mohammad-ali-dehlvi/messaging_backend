from google.cloud.firestore import Client
from fastapi import Depends
from utils.firebase import get_firestore_db, verify_token
from utils.psql import get_db
from sqlalchemy.orm import Session

firestore_dependency: Client = Depends(get_firestore_db)
psql_dependency: Session = Depends(get_db)
user_verify_dependency: dict = Depends(verify_token)