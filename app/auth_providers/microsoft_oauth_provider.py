# import httpx
# from fastapi import HTTPException, status
# from jose import jwt

# from app.core.config import settings


# class MicrosoftOAuthProvider:

#     async def exchange_code(self, code: str, code_verifier: str):

#         async with httpx.AsyncClient() as client:

#             resp = await client.post(
#                 settings.MICROSOFT_TOKEN_URL,
#                 data={
#                     "client_id": settings.MICROSOFT_CLIENT_ID,
#                     "client_secret": settings.MICROSOFT_CLIENT_SECRET,
#                     "code": code,
#                     "grant_type": "authorization_code",
#                     "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
#                     "code_verifier": code_verifier
#                 },
#                 headers={
#                     "Content-Type": "application/x-www-form-urlencoded"
#                 }
#             )

#         if resp.status_code != 200:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Microsoft token exchange failed"
#             )

#         return resp.json()

#     def decode_id_token(self, id_token: str):

#         payload = jwt.get_unverified_claims(id_token)

#         return payload