from twilio.rest import Client
from app.core.config import settings


class SMSService:

    def __init__(self):

        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

    def send_otp(self, phone: str, otp: str):

        message = self.client.messages.create(
            body=f"Your verification code is {otp}",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone
        )

        return message.sid