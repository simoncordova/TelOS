"""Genera un par de claves VAPID nuevo para Web Push (Fase 3 del plan de
migración, rama gamificacion) -- se corre UNA sola vez, a mano, nunca
como parte de un deploy automático: las claves son secretas y no se
guardan en el repo (ver .gitignore), se pasan a `cdk deploy` como
parámetros (VapidPublicKey / VapidPrivateKey NoEcho / VapidSubject),
mismo criterio que el client secret de Cognito hoy.

Formato de las claves (RFC 8292 -- ver api/push.py y
web/src/lib/push.ts):
    pública:  punto EC sin comprimir (65 bytes), base64url sin padding --
              es literal el "applicationServerKey" que
              pushManager.subscribe() del navegador espera.
    privada:  valor crudo de 32 bytes, base64url sin padding -- formato
              que pywebpush (Vapid.from_string) reconoce directo, sin
              necesitar el archivo PEM que genera por default.

Uso (necesita py-vapid/cryptography -- ya vienen con pywebpush, que solo
está en api/requirements.txt, no en el requirements.txt de la raíz que
usa el contenedor de Streamlit; instalalo en tu venv antes de correr
esto si hace falta: `pip install pywebpush`):
    python scripts/generar_claves_vapid.py
"""

import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid02


def _b64url_sin_padding(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def main() -> None:
    vapid = Vapid02()
    vapid.generate_keys()

    clave_privada_cruda = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    clave_publica_cruda = vapid.public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint,
    )
    assert isinstance(vapid.private_key.curve, ec.SECP256R1)  # RFC 8292 exige P-256

    print("--- Claves VAPID nuevas -- guardalas en un lugar seguro, no en el repo ---")
    print(f"VapidPublicKey:  {_b64url_sin_padding(clave_publica_cruda)}")
    print(f"VapidPrivateKey: {_b64url_sin_padding(clave_privada_cruda)}")
    print()
    print("VapidSubject: poné un mailto: o https: real que identifique a quién")
    print("contactar si un proveedor de push (Chrome/FCM, etc.) necesita avisar algo")
    print("-- ej. mailto:tu-email@ejemplo.com")


if __name__ == "__main__":
    main()
