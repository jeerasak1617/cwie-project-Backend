"""
LINE Login Service - OAuth 2.0 flow
"""
import httpx
from app.core.config import settings


class LineLoginService:
    def get_login_url(self, state: str = "cwie_login") -> str:
        params = {
            "response_type": "code",
            "client_id": settings.LINE_CHANNEL_ID,
            "redirect_uri": settings.LINE_CALLBACK_URL,
            "state": state,
            "scope": "profile openid email",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{settings.LINE_AUTH_URL}?{query}"

    async def get_access_token(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.LINE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.LINE_CALLBACK_URL,
                    "client_id": settings.LINE_CHANNEL_ID,
                    "client_secret": settings.LINE_CHANNEL_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code != 200:
                raise Exception(f"LINE token error: {response.text}")
            return response.json()

    async def get_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                settings.LINE_PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                raise Exception(f"LINE profile error: {response.text}")
            return response.json()


line_login_service = LineLoginService()