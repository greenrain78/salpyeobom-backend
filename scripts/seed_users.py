"""데모 admin 계정 시드 스크립트.

사용법: uv run python scripts/seed_users.py

멱등 — 같은 username 의 User 가 이미 있으면 skip.
admin 계정을 재생성하고 싶다면 DB 에서 해당 행을 수동으로 제거 후 다시 실행.
"""

import asyncio
import sys

from tortoise import Tortoise

sys.path.insert(0, ".")
from app.core.security import hash_password
from app.database import TORTOISE_ORM
from app.models.user import User

# 데모/개발용 계정. password 는 평문(시드 시 hash 적용).
# 운영 배포에는 절대 사용 금지 — .env 의 SECRET_KEY 와 별개로 노출되는 자격증명.
USERS = [
    {
        # 데모 계정 — admin / admin1234 로 로그인.
        # `.local` TLD 는 pydantic EmailStr (RFC 6762) 검증에서 거부되므로
        # 반드시 example.com 같이 일반적으로 허용되는 도메인을 사용한다.
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin1234",
    },
]


async def seed_users() -> None:
    await Tortoise.init(config=TORTOISE_ORM)

    created = 0
    for data in USERS:
        _, was_created = await User.get_or_create(
            username=data["username"],
            defaults={
                "email": data["email"],
                "hashed_password": hash_password(data["password"]),
            },
        )
        if was_created:
            created += 1
            print(f"사용자 생성: {data['username']} / {data['password']}")

    print(f"사용자: {created}명 생성 (총 {await User.all().count()}명)")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed_users())
