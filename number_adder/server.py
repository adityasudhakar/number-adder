"""FastAPI server for number-adder with GDPR compliance."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated, Optional

from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
import stripe
import posthog
import uvicorn

from number_adder import add, multiply
from number_adder import database as db

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Stripe configuration
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")  # Price ID for premium upgrade

# PostHog configuration
POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY", "")
if POSTHOG_API_KEY:
    posthog.project_api_key = POSTHOG_API_KEY
    posthog.host = "https://us.i.posthog.com"  # or eu.i.posthog.com for EU

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"

# Security
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# FastAPI app
app = FastAPI(
    title="Number Adder API",
    description="A simple number adding service with GDPR compliance",
    version="0.3.0"
)

# CORS middleware - allow mobile app and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


class MultiplyRequest(BaseModel):
    a: float
    b: float


class MultiplyResponse(BaseModel):
    a: float
    b: float
    result: float


class ApiKeyResponse(BaseModel):
    api_key: str
    message: str


class ApiKeyStatusResponse(BaseModel):
    has_api_key: bool


# Analytics helper
def track_event(user_id: int, event: str, properties: dict = None):
    """Track an event in PostHog if configured."""
    if POSTHOG_API_KEY:
        posthog.capture(
            distinct_id=str(user_id),
            event=event,
            properties=properties or {}
        )


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


def hash_api_key(key: str) -> str:
    """Hash an API key with SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


def get_current_user_id_flexible(
    api_key: Annotated[Optional[str], Depends(api_key_header)] = None,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(HTTPBearer(auto_error=False))] = None,
) -> int:
    """Extract user ID from API key or JWT token.

    Tries X-API-Key header first, then falls back to Bearer JWT token.
    """
    # Try API key first
    if api_key:
        key_hash = hash_api_key(api_key)
        user = db.get_user_by_api_key_hash(key_hash)
        if user:
            return user["id"]
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Fall back to JWT
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a Bearer token or X-API-Key header."
    )


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

    # Track signup
    track_event(user_id, "user_signed_up", {"method": "email"})

    # Return token
    token = create_access_token(user_id)
    return Token(access_token=token, token_type="bearer")


@app.post("/login", response_model=Token)
def login(user: UserLogin):
    """Login and get access token."""
    db_user = db.get_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    track_event(db_user["id"], "user_logged_in", {"method": "email"})
    token = create_access_token(db_user["id"])
    return Token(access_token=token, token_type="bearer")


# Calculator endpoints
@app.post("/add", response_model=AddResponse)
def add_numbers(
    request: AddRequest,
    user_id: Annotated[int, Depends(get_current_user_id_flexible)]
):
    """Add two numbers (requires authentication)."""
    result = add(request.a, request.b)

    # Save to history
    db.save_calculation(user_id, request.a, request.b, result, operation="add")

    # Track calculation
    track_event(user_id, "calculation", {"operation": "add", "a": request.a, "b": request.b, "result": result})

    return AddResponse(a=request.a, b=request.b, result=result)


@app.post("/multiply", response_model=MultiplyResponse)
def multiply_numbers(
    request: MultiplyRequest,
    user_id: Annotated[int, Depends(get_current_user_id_flexible)]
):
    """Multiply two numbers (requires premium subscription)."""
    # Check if user is premium
    user = db.get_user_by_id(user_id)
    if not user or not user.get("is_premium"):
        raise HTTPException(
            status_code=403,
            detail="Premium subscription required. Use /create-checkout-session to upgrade."
        )

    result = multiply(request.a, request.b)

    # Save to history
    db.save_calculation(user_id, request.a, request.b, result, operation="multiply")

    # Track calculation
    track_event(user_id, "calculation", {"operation": "multiply", "a": request.a, "b": request.b, "result": result})

    return MultiplyResponse(a=request.a, b=request.b, result=result)


@app.get("/history")
def get_history(user_id: Annotated[int, Depends(get_current_user_id_flexible)]):
    """Get calculation history for current user."""
    calculations = db.get_user_calculations(user_id)
    return {"calculations": calculations}


# Stripe endpoints
@app.post("/create-checkout-session")
def create_checkout_session(
    user_id: Annotated[int, Depends(get_current_user_id)],
    success_url: str = "https://example.com/success",
    cancel_url: str = "https://example.com/cancel"
):
    """Create a Stripe checkout session for premium upgrade."""
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_premium"):
        raise HTTPException(status_code=400, detail="Already premium")

    # Get or create Stripe customer
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(email=user["email"])
        customer_id = customer.id
        db.set_stripe_customer_id(user_id, customer_id)

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user_id)},
    )

    # Track upgrade started
    track_event(user_id, "upgrade_started", {"session_id": session.id})

    return {"checkout_url": session.url, "session_id": session.id}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle successful payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        if user_id:
            db.upgrade_user_to_premium(int(user_id))
            track_event(int(user_id), "upgraded_to_premium", {"payment_intent": session.get("payment_intent")})

    return {"status": "success"}


# GDPR endpoints
@app.get("/me")
def get_my_data(user_id: Annotated[int, Depends(get_current_user_id_flexible)]):
    """View my account data (GDPR: Right to Access)."""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/me/export")
def export_my_data(user_id: Annotated[int, Depends(get_current_user_id_flexible)]):
    """Export all my data as JSON (GDPR: Right to Portability)."""
    data = db.export_user_data(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    track_event(user_id, "data_exported")

    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=my_data.json"}
    )


@app.delete("/me")
def delete_my_account(user_id: Annotated[int, Depends(get_current_user_id_flexible)]):
    """Delete my account and all data (GDPR: Right to Erasure)."""
    # Track before deletion (so we still have the user_id)
    track_event(user_id, "account_deleted")

    success = db.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Account and all associated data deleted successfully"}


# API key management endpoints
@app.post("/api-key", response_model=ApiKeyResponse)
def generate_api_key(user_id: Annotated[int, Depends(get_current_user_id)]):
    """Generate a new API key. Invalidates any existing key."""
    raw = secrets.token_hex(16)
    api_key = f"na_{raw}"

    key_hash = hash_api_key(api_key)
    db.set_api_key_hash(user_id, key_hash)

    track_event(user_id, "api_key_generated")

    return ApiKeyResponse(
        api_key=api_key,
        message="API key generated. Save it now — it won't be shown again."
    )


@app.delete("/api-key")
def revoke_api_key(user_id: Annotated[int, Depends(get_current_user_id)]):
    """Revoke the current API key."""
    db.set_api_key_hash(user_id, None)

    track_event(user_id, "api_key_revoked")

    return {"message": "API key revoked successfully"}


@app.get("/api-key/status", response_model=ApiKeyStatusResponse)
def get_api_key_status(user_id: Annotated[int, Depends(get_current_user_id)]):
    """Check if user has an active API key."""
    return ApiKeyStatusResponse(has_api_key=db.has_api_key(user_id))


# Health check
@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Version endpoint
def _read_pyproject_version() -> str:
    """Read version from repo pyproject.toml (best-effort)."""
    try:
        import tomllib  # py3.11+
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text("utf-8"))
        return str(data.get("project", {}).get("version") or "unknown")
    except Exception:
        return "unknown"


def _read_git_sha():
    """Get git sha from env or from git (best-effort)."""
    sha = os.environ.get("GIT_SHA") or os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        return out.decode().strip()
    except Exception:
        return None


@app.get("/version")
def version():
    """Return application version and git sha (if available)."""
    return {
        "version": _read_pyproject_version(),
        "git_sha": _read_git_sha(),
    }


# Google OAuth endpoints
@app.get("/auth/google")
def google_login():
    """Redirect to Google OAuth."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=email%20profile"
        "&access_type=offline"
    )
    return RedirectResponse(url=google_auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str):
    """Handle Google OAuth callback."""
    import httpx

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get tokens from Google")

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        user_info = user_response.json()
        email = user_info.get("email")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Find or create user
        db_user = db.get_user_by_email(email)
        if not db_user:
            # Create new user with random password (they'll use OAuth to login)
            import secrets
            random_password = secrets.token_urlsafe(32)
            password_hash = hash_password(random_password)
            user_id = db.create_user(email, password_hash)
        else:
            user_id = db_user["id"]

        # Track signup/login
        if not db_user:
            track_event(user_id, "user_signed_up", {"method": "google"})
        else:
            track_event(user_id, "user_logged_in", {"method": "google"})

        # Create JWT token
        token = create_access_token(user_id)

        # Redirect to dashboard with token
        return RedirectResponse(
            url=f"/dashboard.html?token={token}",
            status_code=302
        )


class GoogleTokenRequest(BaseModel):
    id_token: str


@app.post("/auth/google/mobile")
async def google_mobile_auth(request: GoogleTokenRequest):
    """Authenticate with Google ID token (for mobile apps)."""
    try:
        # Verify the ID token with Google
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={request.id_token}"
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google token")

            token_info = response.json()
            email = token_info.get("email")

            if not email:
                raise HTTPException(status_code=400, detail="Email not in token")

            # Find or create user
            db_user = db.get_user_by_email(email)
            if not db_user:
                import secrets
                random_password = secrets.token_urlsafe(32)
                password_hash = hash_password(random_password)
                user_id = db.create_user(email, password_hash)
                track_event(user_id, "user_signed_up", {"method": "google_mobile"})
            else:
                user_id = db_user["id"]
                track_event(user_id, "user_logged_in", {"method": "google_mobile"})

            # Create JWT token
            token = create_access_token(user_id)

            return {"access_token": token, "token_type": "bearer"}
    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="Failed to verify token with Google")


# Serve static files
@app.get("/api-docs")
def serve_api_docs():
    """Serve the API documentation page."""
    return FileResponse(STATIC_DIR / "api-docs.html")


@app.get("/")
def serve_index():
    """Serve the landing page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{filename:path}")
def serve_static(filename: str):
    """Serve static files."""
    file_path = STATIC_DIR / filename
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    # If file not found, return index.html for SPA routing
    return FileResponse(STATIC_DIR / "index.html")


def main():
    """Run the server."""
    print("Starting Number Adder API server...")
    print("API docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
