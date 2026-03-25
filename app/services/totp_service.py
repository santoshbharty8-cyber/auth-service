import pyotp
import base64
import qrcode
from io import BytesIO


class TOTPService:

    def generate_secret(self):

        return pyotp.random_base32()

    def build_uri(self, email, secret):

        totp = pyotp.TOTP(secret)

        return totp.provisioning_uri(
            name=email,
            issuer_name="AuthSystem"
        )

    def generate_qr(self, uri):

        img = qrcode.make(uri)

        buffer = BytesIO()

        img.save(buffer, format="PNG")

        return base64.b64encode(
            buffer.getvalue()
        ).decode()

    def verify(self, secret, code):

        totp = pyotp.TOTP(secret)

        return totp.verify(code)