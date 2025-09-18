import asyncio
import httpx
from pathlib import Path


SIGEX_API = "https://sigex.kz/api"


class Sigex:
    @staticmethod
    async def send_to_sigex(document_name: str, cms: str, file_bytes: bytes):
        async with httpx.AsyncClient() as client:
            # 1. Регистрация документа
            json_payload = {
                "title": document_name[:10],
                "description": "Документ SemguAIS",
                "signType": "cms",
                "signature": cms
            }
            response = await client.post(SIGEX_API, json=json_payload)
            result = response.json()
            document_id = result["documentId"]

            # 2. Загрузка оригинального файла
            upload_url = f"{SIGEX_API}/{document_id}/data"
            await client.post(upload_url, content=file_bytes, headers={"Content-Type": "application/octet-stream"})

            # 3. Получение информации о документе
            response = await client.get(f"{SIGEX_API}/{document_id}")
            doc_info = response.json()
            sign_id = doc_info["signatures"][0]["signId"]

            # 4. Получение финальной подписи
            signature_url = f"{SIGEX_API}/{document_id}/signature/{sign_id}?signFormat=0"
            response = await client.get(signature_url)
            final_signature = response.json()["signature"]

            return {
                "sigex_document_id": document_id,
                "sigex_cms": final_signature
            }
