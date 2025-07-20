from fastapi import HTTPException, status

def check_admin_user(email: str):
    if email != "alidehlvi082@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not admin"
        )
    return True