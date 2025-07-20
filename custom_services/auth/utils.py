

from firebase_admin import auth
from custom_services.auth.schemas import BaseResponseModel, CreateUserModel, DeleteUserModel
from utils.psql.models import User
from google.cloud.firestore import Client
from sqlalchemy.orm import Session
from google.cloud.firestore import DocumentReference


def create_user_util(request: CreateUserModel, db: Client, psql_db: Session ):
    # Firebase auth
    user_record: auth.UserRecord = auth.create_user(
        email=request.email, 
        password=request.password, 
        display_name=request.display_name,
        email_verified=request.email_verified
    )

    # Psql db
    user = User(email=request.email, display_name=request.display_name)
    psql_db.add(user)
    psql_db.commit()
    psql_db.refresh(user)
    
    # Firestore collection
    uid = user_record.uid
    email = user_record.email
    display_name = user_record.display_name
    db.collection("users").add(document_data = {
        "uid": uid,
        "email": email,
        "display_name": display_name
    }, document_id=uid)

    return BaseResponseModel(success=True, message="User created")


def delete_user_util(request: DeleteUserModel, db: Client, psql_db: Session):
    email = request.email

    # Firebase auth
    user: auth.UserRecord = auth.get_user_by_email(email)
    auth.delete_user(user.uid)

    # Psql db
    sql_user = psql_db.query(User).filter(User.email == email).first()
    if sql_user:
        psql_db.delete(sql_user)
        psql_db.commit()

    # Firestore collection
    user_doc: DocumentReference = db.collection("users").document(user.uid)
    user_doc.delete()

    return BaseResponseModel(success=True, message="User deleted")