from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env(원격/기본) → .env.local(로컬 개발용) 순서로 로드.
    # 같은 키가 있으면 뒤 파일(.env.local)이 우선한다.
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

    DATABASE_URL: str = "postgres://user:pass@localhost:5432/salpyeobom"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12 hours

    # 쉼표로 구분된 허용 Origin 목록
    # 예) CORS_ORIGINS=https://example.com,https://admin.example.com
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5500"

    # ── 이메일(Resend) 설정 ───────────────────────────────────
    # 보고서 이메일 전송에 사용. 값은 .env / .env.local 에서 채운다.
    # RESEND_API_KEY: https://resend.com/api-keys 에서 발급.
    # RESEND_FROM: 발신 주소. 도메인(salpyeobom.kro.kr)을 Resend 에서 인증해야 외부 수신자에게 발송 가능.
    #   인증 전에는 테스트 발신자(onboarding@resend.dev)로만, Resend 계정 소유자 본인 이메일에 한해 발송됨.
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "살펴봄 <noreply@salpyeobom.kro.kr>"


settings = Settings()
