from email.message import EmailMessage

import aiosmtplib
import httpx

from app.core.config import get_settings


async def send_email(*, to: str, subject: str, html_body: str) -> None:
    """Send transactional email via Resend in prod, MailHog/SMTP in dev.

    Never raises to the caller on delivery failure — auth flows (verification,
    password reset) must not 500 just because outbound mail is degraded; the
    token is still valid and can be resent.
    """
    settings = get_settings()

    try:
        if settings.resend_api_key:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.resend_api_key.get_secret_value()}"
                    },
                    json={
                        "from": "VeriHire <notifications@verihire.app>",
                        "to": [to],
                        "subject": subject,
                        "html": html_body,
                    },
                )
        else:
            message = EmailMessage()
            message["From"] = "notifications@verihire.local"
            message["To"] = to
            message["Subject"] = subject
            message.set_content("This email requires an HTML-capable client.")
            message.add_alternative(html_body, subtype="html")

            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host or "localhost",
                port=settings.smtp_port,
            )
    except (httpx.HTTPError, OSError):
        pass
