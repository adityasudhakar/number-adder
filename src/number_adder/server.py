"""FastAPI server for number-adder with GDPR compliance."""

import os
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
import uvicorn

from number_adder import add
from number_adder import database as db

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security
security = HTTPBearer()

# FastAPI app
app = FastAPI(
    title="Number Adder API",
    description="A simple number adding service with GDPR compliance",
    version="0.2.0"
)


# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class AddRequest(BaseModel):
    a: float
    b: float


class AddResponse(BaseModel):
    a: float
    b: float
    result: float


# Auth helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    """Extract user ID from JWT token."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Startup event
@app.on_event("startup")
def startup():
    db.init_db()


# Auth endpoints
@app.post("/register", response_model=Token)
def register(user: UserRegister):
    """Register a new user account."""
    # Check if user exists
    if db.get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    password_hash = hash_password(user.password)
    user_id = db.create_user(user.email, password_hash)

    # Return token
    token = create_access_token(user_id)
    return Token(access_token=token, token_type="bearer")


@app.post("/login", response_model=Token)
def login(user: UserLogin):
    """Login and get access token."""
    db_user = db.get_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(db_user["id"])
    return Token(access_token=token, token_type="bearer")


# Calculator endpoints
@app.post("/add", response_model=AddResponse)
def add_numbers(
    request: AddRequest,
    user_id: Annotated[int, Depends(get_current_user_id)]
):
    """Add two numbers (requires authentication)."""
    result = add(request.a, request.b)

    # Save to history
    db.save_calculation(user_id, request.a, request.b, result)

    return AddResponse(a=request.a, b=request.b, result=result)


@app.get("/history")
def get_history(user_id: Annotated[int, Depends(get_current_user_id)]):
    """Get calculation history for current user."""
    calculations = db.get_user_calculations(user_id)
    return {"calculations": calculations}


# GDPR endpoints
@app.get("/me")
def get_my_data(user_id: Annotated[int, Depends(get_current_user_id)]):
    """View my account data (GDPR: Right to Access)."""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/me/export")
def export_my_data(user_id: Annotated[int, Depends(get_current_user_id)]):
    """Export all my data as JSON (GDPR: Right to Portability)."""
    data = db.export_user_data(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=my_data.json"}
    )


@app.delete("/me")
def delete_my_account(user_id: Annotated[int, Depends(get_current_user_id)]):
    """Delete my account and all data (GDPR: Right to Erasure)."""
    success = db.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Account and all associated data deleted successfully"}


# Health check
@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """Run the server."""
    print("Starting Number Adder API server...")
    print("API docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
