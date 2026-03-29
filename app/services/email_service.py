import smtplib
from email.mime.text import MIMEText
from app.core.config import settings


class EmailService:

    def send_otp_email(self, to_email: str, otp: str):
        subject = "Your OTP Code"
        body = f"""
        <h3>Your OTP Code</h3>
        <p>Your OTP is: <b>{otp}</b></p>
        <p>This OTP will expire in 5 minutes.</p>
        """

        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = settings.MAIL_FROM
        msg["To"] = to_email

        try:
            with smtplib.SMTP(settings.MAILTRAP_HOST, settings.MAILTRAP_PORT) as server:
                server.starttls()
                server.login(settings.MAILTRAP_USERNAME, settings.MAILTRAP_PASSWORD)
                server.send_message(msg)

        except Exception as e:
            raise Exception(f"Email sending failed: {str(e)}")