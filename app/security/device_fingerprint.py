import hashlib


def generate_device_fingerprint(user_agent: str, ip: str):

    raw = f"{user_agent}:{ip}"

    return hashlib.sha256(raw.encode()).hexdigest()