import requests

from app.schemas import UserEcpInfo


class NCANode:
    NCANODE_URL = 'http://localhost:14579'

    @staticmethod
    def cms_extract(cms: str) -> str | None:
        url = f'{NCANode.NCANODE_URL}/cms/extract'

        payload = {
            'cms': cms
        }

        response = requests.post(url, json=payload)
        data = response.json()

        if response.status_code != 200:
            return None

        return data['data']

    def cms_verify(self, cms: str, original_data: str = None) -> UserEcpInfo | None:
        # if original_data:
        #     if self.cms_extract(cms) != original_data:
        #         return None

        url = f'{NCANode.NCANODE_URL}/cms/verify'

        payload = {
            'revocationCheck': [
                'OCSP'
            ],
            'cms': cms,
            'data': original_data
        }

        response = requests.post(url, json=payload)
        data = response.json()

        signers = data.get('signers', None)

        if signers:
            signers = None if len(signers) == 0 else signers

        is_valid = data.get('valid', False)

        if response.status_code != 200 or signers is None or not is_valid:
            return None

        for signer in signers:



            certificates = signer.get('certificates', None)

            if certificates is not None:
                for certificate in certificates:
                    is_valid = certificate.get('valid', False)

                    if not is_valid:
                        return None

        subject = signers[0]['certificates'][0]['subject']

        return UserEcpInfo(**subject)
