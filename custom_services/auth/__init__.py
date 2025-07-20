from typing import List
from fastapi import APIRouter
from firebase_admin import auth
from google.cloud.firestore import DocumentReference

from utils.psql.models import User
from .utils import create_user_util, delete_user_util
from .schemas import BaseResponseModel, BulkBaseResponseModel, BulkCreateUsersRequest, BulkDeleteUsersRequest, CreateUserModel, DeleteUserModel
from utils.dependencies import firestore_dependency, psql_dependency

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/create_user", response_model=BaseResponseModel)
async def create_user(
    request: CreateUserModel, 
    db=firestore_dependency, 
    psql_db = psql_dependency
):
    return create_user_util(request, db, psql_db)
    
    

@auth_router.post("/delete_user", response_model=BaseResponseModel)
async def delete_user(
    request: DeleteUserModel, 
    db=firestore_dependency,
    psql_db=psql_dependency
):
    return delete_user_util(request, db, psql_db)
    


@auth_router.post("/bulk/create_user", response_model=BulkBaseResponseModel)
async def bulk_create_users(
    request: BulkCreateUsersRequest, 
    db=firestore_dependency, 
    psql_db = psql_dependency
):
    result: List[BaseResponseModel] = []
    users = request.users
    for user_data in users:
        try:
            result.append(create_user_util(user_data, db, psql_db))
        except Exception as e:
            result.append(BaseResponseModel(success=False, message=f"{user_data.email}, {str(e)}"))
    return BulkBaseResponseModel(result=result)


@auth_router.post("/bulk/delete_user", response_model=BulkBaseResponseModel)
async def bulk_delete_users(
    request: BulkDeleteUsersRequest, 
    db=firestore_dependency, 
    psql_db = psql_dependency
):
    result: List[BaseResponseModel] = []
    users = request.users
    for user_data in users:
        try:
            result.append(delete_user_util(user_data, db, psql_db))
        except Exception as e:
            result.append(BaseResponseModel(success=False, message=f"{user_data.email}, {str(e)}"))
    return BulkBaseResponseModel(result=result)
