import os
import base64
import json
import cbor2


from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity
from fido2.webauthn import AttestedCredentialData, Aaguid, AuthenticationResponse
from app.cache.redis_client import redis_client
from app.models.webauthn_credential import WebAuthnCredential
from app.repositories.webauthn_repository import WebAuthnRepository
from app.repositories.user_repository import UserRepository




rp = PublicKeyCredentialRpEntity(
    id="localhost",
    name="Auth System"
)

server = Fido2Server(rp)


class WebAuthnService:

    def __init__(self, webauthn_repo: WebAuthnRepository, user_repo: UserRepository):
        self.webauthn_repo = webauthn_repo
        self.user_repo = user_repo

    def to_base64url(self, data):
        if isinstance(data, str):
            data = data.encode()

        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")
    
    def from_base64url(self, data: str) -> bytes:
        padding = '=' * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)
    
    # def to_base64url(self, data: bytes):
    #     return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")
        
    def start_registration(self, user):

        registration_data, state = server.register_begin(
            {
                "id": str(user.id).encode(),
                "name": user.email,
                "displayName": user.email
            },
            user_verification="preferred"
        )
        
         

        # store state in Redis
        redis_client.setex(
            f"webauthn_reg:{user.id}",
            300,
            json.dumps(state)
        )

        options = registration_data["publicKey"]
        print("Challenge start:", options["challenge"])
       

        return {
            "publicKey": {
                "challenge": options["challenge"],
                "rp": {
                    "name": options["rp"]["name"],
                    "id": options["rp"]["id"]
                },
                "user": {
                    "id": self.to_base64url(options["user"]["id"]),
                    "name": options["user"]["name"],
                    "displayName": options["user"]["displayName"]
                },
                "pubKeyCredParams": [
                    {
                        "type": p["type"],
                        "alg": p["alg"]
                    }
                    for p in options["pubKeyCredParams"]
                ],
                "timeout": 60000,
                "attestation": "none"
            }
        }

    def finish_registration(self, user, credential):

        state_json = redis_client.get(f"webauthn_reg:{user.id}")
        
        if not state_json:
            raise Exception("Registration expired")
        
        state = json.loads(state_json)
        
        auth_data = server.register_complete(
            state,
            credential
        ) 
        
        cred_data = auth_data.credential_data

        credential_id = self.to_base64url(
            cred_data.credential_id
        )

        public_key = base64.b64encode(
            cbor2.dumps(cred_data.public_key)
        ).decode()

        sign_count = auth_data.counter  
         

        cred = WebAuthnCredential(
            user_id=user.id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count
        )
        # Save credential in DB
        saved_cred = self.webauthn_repo.create(cred)

        # 🔐 Delete the challenge after successful verification
        redis_client.delete(f"webauthn_reg:{user.id}")

        return saved_cred
    
    def start_login(self, user):

        credentials = self.webauthn_repo.find_by_user(user.id)
        if not credentials:
            raise Exception("No passkeys registered")

        allow_credentials = [
            {
                "type": "public-key",
                "id": self.from_base64url(c.credential_id)
            }
            for c in credentials
        ]

        auth_data, state = server.authenticate_begin(allow_credentials)
        state_str = base64.b64encode(json.dumps(state).encode()).decode()

        redis_client.setex(
            f"webauthn_login:{user.id}",
            300,
            state_str
        )

        options = auth_data.public_key

        return {
            "publicKey": {
                "challenge": self.to_base64url(options.challenge),
                "rpId": options.rp_id,
                "timeout": options.timeout,
                "userVerification": options.user_verification,
                "allowCredentials": [
                    {
                        "type": cred["type"],
                        "id": self.to_base64url(cred["id"])
                    }
                    for cred in allow_credentials
                ]
            }
        }
    
    def finish_login(self, credential):

        credential_id = credential["id"]

        cred = self.webauthn_repo.find_by_credential_id(credential_id)

        if not cred:
            raise Exception("Credential not found")

        state_b64 = redis_client.get(f"webauthn_login:{cred.user_id}")     

        if not state_b64:
            raise Exception("Login expired")

        state = json.loads(base64.b64decode(state_b64))

        attested_cred = AttestedCredentialData.create(
            aaguid=Aaguid(b"\x00" * 16),
            credential_id=self.from_base64url(cred.credential_id),
            public_key=cbor2.loads(base64.b64decode(cred.public_key)),
        )

        server.authenticate_complete(
            state,
            [attested_cred],
            credential
        )

        # extract counter from client response
        authentication = AuthenticationResponse.from_dict(credential)
        counter = authentication.response.authenticator_data.counter

        # replay protection
        if counter <= cred.sign_count:
            raise Exception("Possible cloned authenticator detected")

        # update counter
        cred.sign_count = counter
        self.webauthn_repo.update(cred)

        # remove login challenge
        redis_client.delete(f"webauthn_login:{cred.user_id}")
        user = self.user_repo.find_by_id(cred.user_id)

        return user