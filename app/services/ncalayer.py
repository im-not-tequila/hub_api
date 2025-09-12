import base64

from base64 import b64decode
from asn1crypto import cms, x509 as asn1_x509

from app.schemas_internal import UserEcpInfo


def _load_signature(base64_signature: str) -> cms.ContentInfo:
    der_data = b64decode(base64_signature)
    content_info = cms.ContentInfo.load(der_data)

    if content_info['content_type'].native != 'signed_data':
        raise ValueError("Неверный формат CMS: ожидается signed_data")

    return content_info


def _get_cert_der(content_info: cms.ContentInfo):
    signed_data = content_info['content']

    certs = signed_data['certificates']
    cert_der = None

    for cert in certs:
        if isinstance(cert.chosen, asn1_x509.Certificate):
            cert_der = cert.chosen
            break

    if cert_der is None:
        raise ValueError("Сертификат не найден в подписи")

    return cert_der


def _get_signature_value(content_info: cms.ContentInfo) -> str:
    signed_data = content_info['content']
    encap_content_info = signed_data['encap_content_info']
    signature_raw = encap_content_info['content'].native
    signature_value = base64.b64encode(signature_raw).decode('utf-8')

    return str(signature_value)


def extract_info(base64_signature: str) -> UserEcpInfo:
    """
    Извлекает информацию о пользователе из сертификата
    """

    content_info = _load_signature(base64_signature)
    cert_der = _get_cert_der(content_info)

    subject = cert_der['tbs_certificate']['subject'].native
    print(subject)

    return UserEcpInfo(**subject)


def check_signed_data(base64_signature: str, original_data: str) -> bool:
    content_info = _load_signature(base64_signature)
    signature_value = _get_signature_value(content_info)

    if original_data == signature_value:
        return True

    return False

