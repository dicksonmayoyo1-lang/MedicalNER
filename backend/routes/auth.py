"""
Authentication routes
"""
from fastapi import APIRouter, HTTPException, Depends, status
from models.schemas import User, UserCreate, UserLogin, Token
from services.auth import AuthService
from dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Register a new user"""
    # Check if username already exists
    existing_user = AuthService.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Register user
    new_user = AuthService.register_user(user)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register user"
        )
    
    return new_user


@router.post("/login", response_model=Token)
async def login_user(user: UserLogin):
    """Login user and return JWT token"""
    authenticated_user = AuthService.authenticate_user(user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    
    token = AuthService.create_token_for_user(authenticated_user)
    return token


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout_user():
    """Logout user (client-side token removal)"""
    return {"message": "Successfully logged out"}

