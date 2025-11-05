from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import os
import hashlib

# PUBLIC_INTERFACE
def get_allowed_origins_from_env() -> List[str]:
    """Return allowed CORS origins from BACKEND_CORS_ORIGINS env or sensible defaults."""
    raw = os.getenv("BACKEND_CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        # Defaults for local dev and CI preview
        origins = ["http://localhost:3000", "https://vscode-internal-10297-beta.beta01.cloud.kavia.ai:3000"]
    return origins


# Configure FastAPI with metadata for OpenAPI/Swagger
app = FastAPI(
    title="Auth API",
    description="Simple authentication API with register and login endpoints.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service health endpoints"},
        {"name": "Auth", "description": "Authentication endpoints"},
    ],
)

# CORS configuration:
# - Default to allowing http://localhost:3000 plus any BACKEND_CORS_ORIGINS provided.
# - Credentials off by default to simplify local dev, can be toggled via BACKEND_CORS_CREDENTIALS=true.
cors_origins = list(set(get_allowed_origins_from_env() + ["http://localhost:3000"]))
allow_credentials_env = os.getenv("BACKEND_CORS_CREDENTIALS", "false").lower() in ("1", "true", "yes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials_env,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"], summary="Health Check")
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint indicating the service is up."""
    return {"message": "Healthy"}


# ---- Models ----
class RegisterRequest(BaseModel):
    name: str = Field(..., description="Full name of the user")
    email: EmailStr = Field(..., description="User email (unique)")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")


class RegisterResponse(BaseModel):
    message: str = Field(..., description="Result message")
    user: Dict[str, str] = Field(..., description="Created user basic info")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    message: str = Field(..., description="Result message")
    user: Dict[str, str] = Field(..., description="Basic user info")


# ---- Simple In-Memory User Store (for demo) ----
_USERS: Dict[str, Dict[str, str]] = {}


def _hash_password(pw: str) -> str:
    # NOTE: Demo-only hashing. In production use passlib/bcrypt/argon2.
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# PUBLIC_INTERFACE
@app.post(
    "/register",
    response_model=RegisterResponse,
    tags=["Auth"],
    summary="Register a new user",
    description="Creates a new user account. Returns a confirmation message and basic user info.",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "User already exists"},
    },
)
def register_user(payload: RegisterRequest):
    """Register user with email and password. Returns 400 if email already exists."""
    email = payload.email.lower()
    if email in _USERS:
        raise HTTPException(status_code=400, detail="User already exists")

    _USERS[email] = {
        "name": payload.name,
        "email": email,
        "password_hash": _hash_password(payload.password),
    }
    return RegisterResponse(message="User registered", user={"name": payload.name, "email": email})


# PUBLIC_INTERFACE
@app.post(
    "/login",
    response_model=LoginResponse,
    tags=["Auth"],
    summary="Login",
    description="Authenticates a user by email and password. Returns basic user info.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        404: {"description": "User not found"},
    },
)
def login_user(payload: LoginRequest):
    """Login user with email and password. Returns 401 for invalid credentials."""
    email = payload.email.lower()
    user = _USERS.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user["password_hash"] != _hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(message="Login successful", user={"name": user["name"], "email": email})
