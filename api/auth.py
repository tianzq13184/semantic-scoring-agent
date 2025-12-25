"""
Simplified permission system
Supports two roles: student and teacher
"""
from enum import Enum
from typing import Optional
from fastapi import HTTPException, Header, Depends
from .db import SessionLocal, User

class UserRole(str, Enum):
    """User role"""
    STUDENT = "student"  # Student: answer questions, browse results
    TEACHER = "teacher"  # Teacher: manage, grade


def get_current_user(token: Optional[str] = Header(None, alias="X-User-Token")) -> Optional[dict]:
    """
    Get current user from request header
    Simplified implementation: use X-User-Token header to pass user ID
    Production environment should use more secure authentication methods like JWT
    """
    if not token:
        return None
    
    sess = SessionLocal()
    try:
        user = sess.query(User).filter(User.id == token).first()
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        return None
    finally:
        sess.close()


def require_role(allowed_roles: list[UserRole]):
    """
    Permission check decorator
    Only allows users with specified roles to access
    """
    def role_checker(current_user: Optional[dict] = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(status_code=401, detail="Login required")
        
        user_role = UserRole(current_user["role"])
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required roles: {', '.join([r.value for r in allowed_roles])}"
            )
        
        return current_user
    
    return role_checker


# Convenient permission check dependencies
require_teacher = require_role([UserRole.TEACHER])
require_student = require_role([UserRole.STUDENT])
require_any = require_role([UserRole.STUDENT, UserRole.TEACHER])

