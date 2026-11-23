"""QR decoding for images and a local camera."""

import logging

import cv2
import numpy as np


logger = logging.getLogger(__name__)


class QRReaderError(Exception):
    """An expected QR image or camera reading error."""


def decode_qr_image(image_bytes: bytes) -> str:
    if not image_bytes:
        raise QRReaderError("A imagem selecionada está vazia.")
    try:
        image = cv2.imdecode(
            np.frombuffer(image_bytes, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        if image is None:
            raise QRReaderError("Não foi possível abrir a imagem selecionada.")
        detector = cv2.QRCodeDetector()
        value, _, _ = detector.detectAndDecode(image)
        if not value.strip() and max(image.shape[:2]) <= 1000:
            border = max(8, min(image.shape[:2]) // 16)
            padded = cv2.copyMakeBorder(
                image,
                border,
                border,
                border,
                border,
                cv2.BORDER_CONSTANT,
                value=(255, 255, 255),
            )
            enlarged = cv2.resize(
                padded,
                None,
                fx=2,
                fy=2,
                interpolation=cv2.INTER_NEAREST,
            )
            value, _, _ = detector.detectAndDecode(enlarged)
    except cv2.error as exc:
        logger.exception("Could not decode QR code from image")
        raise QRReaderError("Não foi possível descodificar a imagem.") from exc
    if not value.strip():
        raise QRReaderError("Não foi encontrado um código QR na imagem.")
    return value.strip()


def scan_qr_with_camera() -> str | None:
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        raise QRReaderError(
            "Não foi possível aceder à câmara. Verifique a ligação e as permissões."
        )

    try:
        detector = cv2.QRCodeDetector()
        while True:
            success, frame = camera.read()
            if not success:
                raise QRReaderError("Não foi possível obter imagem da câmara.")

            value, points, _ = detector.detectAndDecode(frame)
            if value.strip():
                return value.strip()
            if points is not None:
                points = points.astype(int).reshape(-1, 2)
                for index, point in enumerate(points):
                    next_point = points[(index + 1) % len(points)]
                    cv2.line(
                        frame,
                        tuple(point),
                        tuple(next_point),
                        (0, 255, 0),
                        2,
                    )

            cv2.imshow("Leitor de código QR - prima Q para fechar", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                return None
    except cv2.error as exc:
        logger.exception("Could not read QR code from camera")
        raise QRReaderError("Ocorreu um erro ao ler a câmara.") from exc
    finally:
        camera.release()
        cv2.destroyAllWindows()
