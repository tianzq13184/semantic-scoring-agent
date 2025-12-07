"""
简化的权限系统
支持两个角色：学生（student）和老师（teacher）
"""
from enum import Enum
from typing import Optional
from fastapi import HTTPException, Header, Depends
from .db import SessionLocal, User

class UserRole(str, Enum):
    """用户角色"""
    STUDENT = "student"  # 学生：答题、浏览结果
    TEACHER = "teacher"  # 老师：管理、判分


def get_current_user(token: Optional[str] = Header(None, alias="X-User-Token")) -> Optional[dict]:
    """
    从请求头获取当前用户
    简化实现：使用 X-User-Token 头传递用户ID
    实际生产环境应该使用JWT等更安全的认证方式
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
    权限检查装饰器
    只允许指定角色的用户访问
    """
    def role_checker(current_user: Optional[dict] = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(status_code=401, detail="需要登录")
        
        user_role = UserRole(current_user["role"])
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"权限不足。需要角色: {', '.join([r.value for r in allowed_roles])}"
            )
        
        return current_user
    
    return role_checker


# 便捷的权限检查依赖
require_teacher = require_role([UserRole.TEACHER])
require_student = require_role([UserRole.STUDENT])
require_any = require_role([UserRole.STUDENT, UserRole.TEACHER])

