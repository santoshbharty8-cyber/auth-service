from sqlalchemy.orm import Session
from app.models.user_device import UserDevice


class DeviceRepository:

    def __init__(self, db: Session):
        self.db = db

    def find_device(self, user_id, fingerprint):

        return self.db.query(UserDevice).filter(
            UserDevice.user_id == user_id,
            UserDevice.fingerprint == fingerprint
        ).first()

    def create_device(self, user_id, fingerprint, user_agent, ip_address):

        device = UserDevice(
            user_id=user_id,
            fingerprint=fingerprint,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)

        return device
