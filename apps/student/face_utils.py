import cv2
import numpy as np
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

# ponytail: InsightFace model loaded lazily once, stays in memory
_face_app = None


def _get_face_app():
    global _face_app
    if _face_app is None:
        from insightface.app import FaceAnalysis
        _face_app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider'],
            allowed_modules=['detection', 'recognition'],
        )
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
    return _face_app


_fernet_instance = None


def _get_fernet():
    """Derive a Fernet key from Django SECRET_KEY for biometric encryption."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    from django.conf import settings
    secret = settings.SECRET_KEY.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'ojt-biometric-encryption-salt',
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))
    _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt_embedding(raw_bytes):
    """Encrypt embedding bytes with Fernet before storing."""
    f = _get_fernet()
    return f.encrypt(raw_bytes)


def decrypt_embedding(encrypted_bytes):
    """Decrypt Fernet-encrypted embedding bytes."""
    f = _get_fernet()
    return f.decrypt(encrypted_bytes)


def detect_face(image_bytes):
    """Detect face and return 512-d InsightFace embedding.

    Returns:
        (embedding, bbox, face_count) or (None, None, 0) if no face found.
        embedding is np.ndarray float32 shape (512,).
        bbox is [x1, y1, x2, y2] or None.
        face_count is the total number of faces detected in the image.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None, None, 0

    app = _get_face_app()
    faces = app.get(img)
    face_count = len(faces)
    if not faces:
        return None, None, 0

    # Largest face by area
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    bbox = face.bbox.astype(int).tolist()
    return face.embedding.astype(np.float32), bbox, face_count


def encode_face(embedding):
    """Serialize 512-d embedding to encrypted bytes for secure storage."""
    raw = embedding.astype(np.float32).tobytes()
    return encrypt_embedding(raw)


def decode_face(encoding_bytes):
    """Decrypt and deserialize encrypted bytes to 512-d embedding."""
    try:
        raw = decrypt_embedding(encoding_bytes)
    except Exception:
        # Fallback: treat as unencrypted raw bytes (legacy data migration)
        raw = encoding_bytes
    return np.frombuffer(raw, dtype=np.float32).copy()


def verify_faces(stored_encoding, new_embedding, threshold=0.55):
    """Compare embeddings via FAISS inner-product (cosine on unit vectors).

    Args:
        stored_encoding: serialized embedding bytes
        new_embedding: np.ndarray float32 shape (512,)
        threshold: similarity threshold (higher = stricter)

    Returns:
        (is_match: bool, similarity: float)
    """
    stored = decode_face(stored_encoding)

    stored_norm = stored / (np.linalg.norm(stored) + 1e-9)
    new_norm = new_embedding / (np.linalg.norm(new_embedding) + 1e-9)
    similarity = float(np.dot(stored_norm, new_norm))

    return similarity >= threshold, similarity
