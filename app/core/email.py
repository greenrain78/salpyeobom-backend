"""보고서 이메일 전송 서비스 — .docx → PDF 변환 후 Resend API 로 발송.

라우터는 비즈니스 로직(파일 경로 해석·변환·발송)을 직접 다루지 않고
이 모듈의 `send_report_email` 만 호출한다.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import anyio
import resend

from app.config import settings
from app.core.exceptions import EmailSendFailed, ReportNotFound

logger = logging.getLogger(__name__)

# scripts/report_generate.py 와 동일한 산출물 경로 (out/reports/)
OUT_DIR = Path(__file__).resolve().parents[2] / "out" / "reports"
DEFAULT_REPORT = "위험예측보고서_661.docx"


def resolve_report(report_name: str | None) -> Path:
    """보고서 파일 경로를 안전하게 해석한다.

    경로 탈출(`../`)을 차단하고, OUT_DIR 하위의 실제 파일만 허용한다.
    이메일 발송과 PDF 조회 서빙(`routers/reports.py`)이 함께 사용한다.
    """
    name = report_name or DEFAULT_REPORT
    path = (OUT_DIR / name).resolve()
    out_dir = OUT_DIR.resolve()
    if out_dir not in path.parents or not path.is_file():
        raise ReportNotFound()
    return path


def docx_to_pdf(docx: Path) -> Path:
    """LibreOffice headless 로 .docx 를 PDF 로 변환한다 (동기·블로킹).

    시스템에 `soffice`(libreoffice) 가 설치되어 있어야 한다.
    """
    pdf = docx.with_suffix(".pdf")
    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(docx.parent),
                str(docx),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as err:
        logger.error("PDF 변환 실패: %s", err)
        raise EmailSendFailed() from err
    if not pdf.is_file():
        logger.error("PDF 변환 후 산출물이 없음: %s", pdf)
        raise EmailSendFailed()
    return pdf


def _send_via_resend(params: resend.Emails.SendParams) -> None:
    """Resend API 동기 호출 (스레드에서 실행). API 키는 호출 시점에 주입."""
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(params)


async def send_report_email(
    recipient: str,
    report_name: str | None = None,
    subject: str | None = None,
    message: str | None = None,
) -> str:
    """보고서를 PDF 로 변환해 수신자에게 이메일로 발송한다.

    Returns:
        발송에 사용된 보고서 파일명.
    """
    docx = resolve_report(report_name)
    # 블로킹 변환은 스레드로 오프로드해 이벤트 루프를 막지 않는다.
    pdf = await anyio.to_thread.run_sync(docx_to_pdf, docx)

    body = message or (
        f"안녕하세요,\n\n요청하신 위험 예측 보고서({docx.name})를 첨부합니다.\n\n— 살펴봄"
    )
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM,
        "to": [recipient],
        "subject": subject or "[살펴봄] 위험 예측 보고서",
        "text": body,
        "attachments": [
            {
                "filename": pdf.name,
                "content": list(pdf.read_bytes()),  # Resend: 바이트 버퍼(정수 리스트)
                "content_type": "application/pdf",
            }
        ],
    }
    try:
        # SDK 는 동기이므로 스레드로 오프로드해 이벤트 루프를 막지 않는다.
        await anyio.to_thread.run_sync(_send_via_resend, params)
    except EmailSendFailed:
        raise
    except Exception as err:  # 인증/네트워크/API 오류를 일관된 502 로 래핑
        logger.error("이메일 발송 실패: %s", err)
        raise EmailSendFailed() from err
    return docx.name
