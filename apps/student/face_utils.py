import cv2
import numpy as np
import pickle

# Cache the LBPH factory at module level — recreating it on every call is expensive
_recognizer_factory = cv2.face.LBPHFaceRecognizer_create


def detect_face(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(100, 100))
    if len(faces) == 0:
        return None, None
    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (150, 150))
    return face, (x, y, w, h)


def encode_face(face_roi):
    return pickle.dumps(face_roi)


def decode_face(encoding_bytes):
    return pickle.loads(encoding_bytes)


def verify_faces(stored_encoding, new_face_roi, confidence_threshold=90):
    stored_face = decode_face(stored_encoding)
    recognizer = _recognizer_factory()
    recognizer.train([stored_face], np.array([1]))
    label, confidence = recognizer.predict(new_face_roi)
    is_match = confidence < confidence_threshold
    return is_match, confidence
