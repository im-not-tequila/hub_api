import re
import httpx

from fastapi import HTTPException


SIGEX_API = "https://sigex.kz/api"


class Sigex:
    @staticmethod
    async def _get_signature_from_sigex(document_sigex_id: str, signature_id: str):
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            endpoint = f"{SIGEX_API}/{document_sigex_id}/signature/{signature_id}?signFormat=0"

            response = await client.get(endpoint)
            result = response.json()

            return result.get("signature")

    async def register_document(self, document_name: str, user_signature: str, file_bytes: bytes):
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            # 1. Регистрация документа
            document_name_cleaned = re.sub(r"[^\w\s]", " ", document_name)[:10].strip()

            json_payload = {
                "title": document_name_cleaned,
                "description": "Документ SemguAIS",
                "signType": "cms",
                "signature": user_signature
            }

            response = await client.post(SIGEX_API, json=json_payload)
            result = response.json()

            if result.get('message'):
                raise HTTPException(status_code=400, detail="Invalid signature")

            sigex_document_id = result["documentId"]

            # 2. Загрузка оригинального файла
            upload_url = f"{SIGEX_API}/{sigex_document_id}/data"
            await client.post(upload_url, content=file_bytes, headers={"Content-Type": "application/octet-stream"})

            # 3. Получение информации о документе
            response = await client.get(f"{SIGEX_API}/{sigex_document_id}")
            doc_info = response.json()
            sign_id = doc_info["signatures"][0]["signId"]

            # 4. Получение финальной подписи
            sigex_signature = await self._get_signature_from_sigex(sigex_document_id, sign_id)

            return {
                "sigex_document_id": sigex_document_id,
                "sigex_cms": sigex_signature
            }

    async def add_signature(self, sigex_document_id: str, signature: str) -> str | None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            headers = {
                "Content-Type": "application/json"
            }

            endpoint = f"{SIGEX_API}/{sigex_document_id}"

            json_payload = {
                'signType': 'cms',
                'signature': signature
            }

            response = await client.post(endpoint, json=json_payload, headers=headers)
            result = response.json()

            sign_id = result["signId"]
            sigex_signature = await self._get_signature_from_sigex(sigex_document_id, sign_id)

            return sigex_signature
