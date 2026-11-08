import httpx

from app.core.config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if settings.email_dev_mode:
        raise RuntimeError('Email delivery is disabled while EMAIL_DEV_MODE is enabled.')
    if not settings.resend_api_key:
        raise RuntimeError('RESEND_API_KEY is required when EMAIL_DEV_MODE is disabled.')
    response = httpx.post(
        'https://api.resend.com/emails',
        headers={'Authorization': f'Bearer {settings.resend_api_key}'},
        json={
            'from': settings.resend_from_email,
            'to': [to],
            'subject': subject,
            'text': body,
        },
        timeout=10,
    )
    response.raise_for_status()
