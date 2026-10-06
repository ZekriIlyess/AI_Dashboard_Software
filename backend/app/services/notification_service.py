from __future__ import annotations

import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to deliver in-app notifications, emails, and Slack alerts."""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        message: str,
        type: str = "info",
        send_email: bool = False,
        slack_webhook_url: Optional[str] = None
    ) -> Notification:
        """Create a database notification and trigger external alerts if requested."""
        
        # 1. In-app alert creation
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            read=False
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # 2. Asynchronous Slack alert
        if slack_webhook_url or settings.get("SLACK_WEBHOOK_URL"):
            url = slack_webhook_url or settings.get("SLACK_WEBHOOK_URL")
            await NotificationService.send_slack_alert(url, title, message, type)

        # 3. Synchronous/Background email alert
        if send_email:
            # We fetch user email in calling context or run it as a background task.
            # We only send if SMTP configured.
            await NotificationService.send_email_alert(
                recipient_email=settings.get("ALERT_RECIPIENT_EMAIL"),
                title=title,
                message=message
            )

        return notification

    @staticmethod
    async def send_slack_alert(webhook_url: str, title: str, message: str, type: str):
        """Send asynchronous POST request to Slack incoming webhook."""
        try:
            # Choose color based on type
            color = "#3b82f6"  # Blue
            if type == "anomaly":
                color = "#ef4444"  # Red
            elif type == "success":
                color = "#10b981"  # Green
            elif type == "warning":
                color = "#f59e0b"  # Amber

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Nexus AI Alert: {title}",
                        "text": message,
                        "fallback": f"[{type.upper()}] {title} - {message}",
                        "fields": [
                            {"title": "Severity", "value": type.upper(), "short": True}
                        ]
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=5.0)
                if response.status_code != 200:
                    logger.error(f"Slack webhook returned status code {response.status_code}: {response.text}")
        except Exception as exc:
            logger.error(f"Failed to post alert to Slack: {exc}")

    @staticmethod
    async def send_email_alert(recipient_email: Optional[str], title: str, message: str):
        """Send email alert via SMTP (if configured)."""
        smtp_host = settings.get("SMTP_HOST")
        smtp_port = settings.get("SMTP_PORT", 587)
        smtp_user = settings.get("SMTP_USER")
        smtp_password = settings.get("SMTP_PASSWORD")
        from_email = settings.get("SMTP_FROM", "alerts@nexus-ai.com")

        if not all([smtp_host, smtp_user, smtp_password, recipient_email]):
            logger.info("SMTP settings not fully configured. Skipping email delivery.")
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = recipient_email
            msg["Subject"] = f"[Nexus AI] Alert: {title}"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #334155; line-height: 1.6;">
                    <div style="background-color: #4f46e5; padding: 15px; color: #ffffff; font-weight: bold; font-size: 18px;">
                        Nexus AI System Alert
                    </div>
                    <div style="padding: 20px; border: 1px solid #e2e8f0; border-top: none;">
                        <h3>{title}</h3>
                        <p>{message}</p>
                        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
                        <small style="color: #64748b;">This is an automated alert from your Nexus AI deployment.</small>
                    </div>
                </body>
            </html>
            """
            msg.attach(MIMEText(body, "html"))

            # Run in thread pool to not block async loop (smtplib is blocking)
            import anyio
            def _send():
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)

            await anyio.to_thread.run_sync(_send)
            logger.info(f"Alert email sent successfully to {recipient_email}")

        except Exception as exc:
            logger.error(f"Failed to send email alert: {exc}")
