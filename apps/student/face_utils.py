import cv2
import numpy as np
import logging

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


def detect_face(image_bytes):
    """Detect face and return 512-d InsightFace embedding.

    Returns:
        (embedding, bbox) or (None, None) if no face found.
        embedding is np.ndarray float32 shape (512,).
        bbox is [x1, y1, x2, y2] or None.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None, None

    app = _get_face_app()
    faces = app.get(img)
    if not faces:
        return None, None

    # Largest face by area
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    bbox = face.bbox.astype(int).tolist()
    return face.embedding.astype(np.float32), bbox


def encode_face(embedding):
    """Serialize 512-d embedding to bytes."""
    return embedding.astype(np.float32).tobytes()


def decode_face(encoding_bytes):
    """Deserialize bytes to 512-d embedding."""
    return np.frombuffer(encoding_bytes, dtype=np.float32).copy()


def verify_faces(stored_encoding, new_embedding, threshold=0.35):
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
