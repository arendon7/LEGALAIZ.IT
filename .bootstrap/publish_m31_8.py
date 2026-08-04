from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image
import hashlib
import io
import os
import struct
import subprocess
import tarfile
import tempfile

EXPECTED_SHA256 = "8eacac346892b8ef545e8fe21bc562f65425076b01e9181b2f7f990c6c52cef8"
URLS = [
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2Ff302831d-f305-4fbb-b1d5-0f30d498a8b9/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAANuwdAEUNhVixs3lBXBzkG9P6qCqYsRHw63aqDCiQUhI&exp=1785895118&osig=AAAAAAAAAAAAAAAAAAAAAEVV7pAQomXdxn36dGfnvyqblMgGXLbxn6mwVL9Jh2oS&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2Fa8c848e9-cd07-4b8a-957a-aca9601179b1/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAFIHK0OMJJanuTeoZvdfBUIaJVrO1hRT_sgnhpYMoFiz&exp=1785895874&osig=AAAAAAAAAAAAAAAAAAAAAKYXVqPYQXTThTZDPoA4DhuMMl_qInRZha7cX7TOxzgk&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2F3c139de6-bcea-42d1-8cb4-080c9a7bf1c2/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAIFr0uyf5xnQAPdOOvviyKyvc-PG3M_jsV4PkqI9v2B-&exp=1785896812&osig=AAAAAAAAAAAAAAAAAAAAAHpIVMGJd-rthSqY9wlYikm1rp0dW4NGHKHYNY0Q9hZm&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2Fd8614755-151b-46b9-9025-ad239229bd09/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAJs3B9VEdQhxwepb8H8KLfzab-ELpYB0u2FcSXpk12F0&exp=1785898248&osig=AAAAAAAAAAAAAAAAAAAAANErBD0G5fw2vm5p-eX3Pkh3qOqkeFlEMM44ENKwfMQS&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2F0e8b6969-44ea-4389-9183-cb25c387d284/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAOacWA-1QehJLQ5dM6iW33IE3fgFtE0-lGP4mB89C_Bx&exp=1785897672&osig=AAAAAAAAAAAAAAAAAAAAALmjfzDgOT9XVt_1gMSVqIVfqV1Cf3f7FRyeyNyQauT1&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2Fab22c055-1a62-4313-9478-02f5cb2ecc07/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAH-iiF8HTsYUyj_bExDIZY1WQJBJFExE7EqlQ22HHSLK&exp=1785895616&osig=AAAAAAAAAAAAAAAAAAAAAHmA9mTg-uEcpDMl0tsfD8YESiiDsGxaAN4nJw2qr0rX&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2F78aff40f-4eff-46b5-886e-c209c2467af3/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAGveHyl6yTGX8UAM6NfRqfF5XfXDXKAQXxwASpgmVwBB&exp=1785897632&osig=AAAAAAAAAAAAAAAAAAAAABO-dkysJUIrwpmc-gw2T1hB3VzBvJKLOtLXJZL7toM6&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2F38281f1b-1537-4df3-a090-7c2ae371ee17/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAALZakV57W50S6mY6z2P9FAyFK5hJCkVECvi569722SmC&exp=1785895388&osig=AAAAAAAAAAAAAAAAAAAAAHmKmPqAOys5RPyYZSTfExh9k_hukWgQa435fd8vWaqz&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2F7df2df1e-0c1f-40b8-ac19-9aefa2fc17f3/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAACgmhtF-g_uV8_doDFEEvGAU1deXUdShznhRTDp50OP7&exp=1785897578&osig=AAAAAAAAAAAAAAAAAAAAAMs43Eqg1gWN1BdotO57fb03GRSVqxKMm8piViKxRms9&signer=media-rpc&x-canva-quality=thumbnail",
    "https://media.canva.com/v2/image-resize/format:PNG/height:200/quality:100/uri:ifs%3A%2F%2FM%2Ffeed7fe9-c93d-4880-874b-854f8ca953f2/watermark:F/width:200?csig=AAAAAAAAAAAAAAAAAAAAAGgjB3TS47M6E04QjwepJOhI7HffhdthcBDOX_c-ZitG&exp=1785897082&osig=AAAAAAAAAAAAAAAAAAAAAMbbKVH-AYWhGQrlSUgrry-xRRDpgnIIZBzXkhqky0yb&signer=media-rpc&x-canva-quality=thumbnail",
]


def download_chunk(url: str, expected_index: int) -> tuple[int, int, int, bytes]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.canva.com/"})
    with urlopen(request, timeout=45) as response:
        image_bytes = response.read()
    raw = Image.open(io.BytesIO(image_bytes)).convert("RGB").tobytes()
    if raw[:4] != b"LZC1":
        raise RuntimeError(f"Bloque {expected_index}: cabecera inválida")
    index, total, length, archive_size = struct.unpack(">IIIQ", raw[4:24])
    if index != expected_index:
        raise RuntimeError(f"Bloque fuera de orden: {index} != {expected_index}")
    payload = raw[24 : 24 + length]
    if len(payload) != length:
        raise RuntimeError(f"Bloque {index}: longitud incompleta")
    return total, archive_size, length, payload


def main() -> None:
    repo = Path.cwd()
    chunks: dict[int, bytes] = {}
    total_expected: int | None = None
    archive_size_expected: int | None = None

    for index, url in enumerate(URLS):
        total, archive_size, length, payload = download_chunk(url, index)
        if total != len(URLS):
            raise RuntimeError(f"Total inconsistente: {total}")
        total_expected = total
        archive_size_expected = archive_size
        chunks[index] = payload
        print(f"Bloque {index + 1}/{total}: {length} bytes")

    if total_expected is None or archive_size_expected is None:
        raise RuntimeError("No se recuperaron bloques")

    archive = b"".join(chunks[index] for index in range(total_expected))
    if len(archive) != archive_size_expected:
        raise RuntimeError(f"Tamaño inválido: {len(archive)} != {archive_size_expected}")

    digest = hashlib.sha256(archive).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"SHA-256 inválido: {digest}")
    print(f"Paquete completo verificado: {digest}")

    with tempfile.TemporaryDirectory(prefix="legalaiz-m31-8-") as temp_dir:
        temp = Path(temp_dir)
        archive_path = temp / "legalaiz.tar.xz"
        archive_path.write_bytes(archive)
        with tarfile.open(archive_path, mode="r:xz") as bundle:
            bundle.extractall(temp)
        source = temp / "legalaiz_runtime_repo_text"
        if not source.is_dir():
            raise RuntimeError("Árbol fuente no encontrado")
        subprocess.run(
            [
                "rsync",
                "-a",
                "--delete",
                "--exclude=.git",
                "--exclude=.github/workflows",
                f"{source}/",
                f"{repo}/",
            ],
            check=True,
        )

    bootstrap_dir = repo / ".bootstrap"
    if bootstrap_dir.exists():
        subprocess.run(["rm", "-rf", str(bootstrap_dir)], check=True)


if __name__ == "__main__":
    main()
