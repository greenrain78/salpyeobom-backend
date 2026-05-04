from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.exceptions import EmailAlreadyExists, InvalidCredentials, UsernameAlreadyExists
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest) -> UserOut:
    if await User.filter(username=body.username).exists():
        raise UsernameAlreadyExists()
    if await User.filter(email=body.email).exists():
        raise EmailAlreadyExists()
    user = await User.create(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    user = await User.filter(username=body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise InvalidCredentials()
    return TokenResponse(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:  # noqa: B008
    return UserOut.model_validate(current_user)
