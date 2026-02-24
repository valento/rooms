from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.auth import UserLogin, UserRegister, Token, UserResponse
from services.auth import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from services.database import execute_query
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/register")
async def register(user: UserRegister):
    """Register a new user and auto-login."""
    try:
        # Check if user already exists
        check_sql = "SELECT id FROM company.users WHERE email = %s"
        existing = execute_query(check_sql, (user.email,))
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate username from email if not provided
        username = user.username or user.email.split('@')[0]
        
        # Hash password and insert user
        password_hash = get_password_hash(user.password[:72])
        
        insert_sql = """
            INSERT INTO company.users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, email, full_name, role
        """
        
        result = execute_query(
            insert_sql,
            (username, user.email, password_hash, 'author')
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        new_user = result[0]
        
        # Create access token (auto-login)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(new_user['id']), "email": new_user['email']},
            expires_delta=access_token_expires
        )
        
        # Return token + user (same as login)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": new_user['id'],
                "username": new_user['username'],
                "email": new_user['email'],
                "full_name": new_user['full_name'],
                "role": new_user['role']
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login(credentials: UserLogin):
    """Login and receive access token."""
    try:
        # Find user by email
        sql = """
            SELECT id, username, email, full_name, password_hash, role
            FROM company.users 
            WHERE email = %s
        """
        
        result = execute_query(sql, (credentials.email,))
        
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        user = result[0]
        
        # Verify password
        if not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user['id']), "email": user['email']},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "full_name": user['full_name'],
                "role": user['role']
        }}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token."""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        sql = """
            SELECT id, username, email, full_name, role
            FROM company.users 
            WHERE id = %s
        """
        
        result = execute_query(sql, (int(user_id),))
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(**result[0])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
# ---------------------------------------------------------------------------------
# --------- Additional Helper routes ----------------------------------------------
@router.get("/check-email/{email}")
async def check_email_availability(email: str):
    """Check if email is available."""
    sql = "SELECT id FROM company.users WHERE email = %s"
    result = execute_query(sql, (email,))
    
    return {"available": len(result) == 0 if result else True}