"""
Face quality assessment and liveness detection module.

Covers workflow steps:
  - Step 3: Blur detection (Laplacian variance)
  - Step 4: Brightness & contrast checks
  - Step 5: Liveness / anti-spoofing (multi-image variance + screen artifact detection)
  - Step 6: Composite quality gate
"""

import io
import math
from typing import List, Tuple, Optional

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Thresholds (tuned for webcam-quality images)
# ---------------------------------------------------------------------------

BLUR_THRESHOLD = 80.0          # Laplacian variance below this = blurry
BRIGHTNESS_MIN = 40.0          # mean grey below this = too dark
BRIGHTNESS_MAX = 220.0         # mean grey above this = too bright
CONTRAST_MIN = 35.0            # std-dev below this = low contrast / flat lighting
VARIANCE_THRESHOLD = 0.0015    # inter-image cosine similarity variance — below ⇒ likely same photo (spoof)
SCREEN_ARTIFACT_THRESHOLD = 0.12  # frequency-domain energy ratio — above ⇒ screen/moire pattern
FACE_SIZE_MIN_RATIO = 0.15     # face must occupy at least 15% of image area
FACE_SIZE_MAX_RATIO = 0.80     # face should not exceed 80% of image area (too close)
QUALITY_WEIGHTS = {
    "blur": 0.25,
    "brightness": 0.20,
    "contrast": 0.20,
    "liveness": 0.20,
    "face_size": 0.15,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes to BGR numpy array."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def _crop_face(img: np.ndarray, bbox) -> np.ndarray:
    """Crop face region from image using InsightFace bbox (x1,y1,x2,y2)."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return img
    return img[y1:y2, x1:x2]


# ---------------------------------------------------------------------------
# Step 3 — Blur detection
# ---------------------------------------------------------------------------

def detect_blur(image_bytes: bytes, face_bbox=None) -> Tuple[bool, float, str]:
    """
    Detect image blur via Laplacian variance.

    Returns:
        (passed, score, message)
        score: higher = sharper (we invert internally for the quality gate)
    """
    img = _bytes_to_bgr(image_bytes)
    if face_bbox is not None:
        img = _crop_face(img, face_bbox)
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(grey, cv2.CV_64F).var()
    passed = variance >= BLUR_THRESHOLD
    msg = (
        f"Blur score: {variance:.1f} (threshold: {BLUR_THRESHOLD})"
        if passed
        else f"Image is too blurry (score: {variance:.1f}, need ≥{BLUR_THRESHOLD})"
    )
    return passed, variance, msg


# ---------------------------------------------------------------------------
# Step 4 — Brightness & contrast
# ---------------------------------------------------------------------------

def assess_brightness_contrast(image_bytes: bytes, face_bbox=None) -> Tuple[bool, float, float, str]:
    """
    Check brightness (mean) and contrast (std-dev) of the face region.

    Returns:
        (passed, brightness, contrast, message)
    """
    img = _bytes_to_bgr(image_bytes)
    if face_bbox is not None:
        img = _crop_face(img, face_bbox)
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64)
    brightness = float(np.mean(grey))
    contrast = float(np.std(grey))

    issues = []
    if brightness < BRIGHTNESS_MIN:
        issues.append(f"too dark (brightness={brightness:.0f}, need ≥{BRIGHTNESS_MIN})")
    elif brightness > BRIGHTNESS_MAX:
        issues.append(f"too bright (brightness={brightness:.0f}, need ≤{BRIGHTNESS_MAX})")
    if contrast < CONTRAST_MIN:
        issues.append(f"low contrast (contrast={contrast:.0f}, need ≥{CONTRAST_MIN})")

    passed = len(issues) == 0
    msg = "Brightness & contrast OK" if passed else "; ".join(issues)
    return passed, brightness, contrast, msg


# ---------------------------------------------------------------------------
# Step 4b — Face size check
# ---------------------------------------------------------------------------

def check_face_size(image_bytes: bytes, face_bbox) -> Tuple[bool, float, str]:
    """
    Check that the face occupies an appropriate portion of the image.
    
    Too small: face is too far from camera, low resolution for recognition
    Too large: face is too close, may be cropped or distorted
    
    Returns:
        (passed, size_ratio, message)
        size_ratio: face area / image area (0.0 to 1.0)
    """
    if face_bbox is None:
        return True, 0.0, "No face bbox available for size check"
    
    img = _bytes_to_bgr(image_bytes)
    h, w = img.shape[:2]
    image_area = h * w
    
    x1, y1, x2, y2 = [int(v) for v in face_bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    face_width = x2 - x1
    face_height = y2 - y1
    face_area = face_width * face_height
    
    size_ratio = face_area / image_area if image_area > 0 else 0.0
    
    if size_ratio < FACE_SIZE_MIN_RATIO:
        passed = False
        msg = f"Face too small ({size_ratio:.1%} of image, need ≥{FACE_SIZE_MIN_RATIO:.0%}) — move closer to camera"
    elif size_ratio > FACE_SIZE_MAX_RATIO:
        passed = False
        msg = f"Face too large ({size_ratio:.1%} of image, need ≤{FACE_SIZE_MAX_RATIO:.0%}) — move back from camera"
    else:
        passed = True
        msg = f"Face size OK ({size_ratio:.1%} of image)"
    
    return passed, size_ratio, msg


# ---------------------------------------------------------------------------
# Step 5 — Liveness / anti-spoofing
# ---------------------------------------------------------------------------

def _detect_screen_artifacts(image_bytes: bytes) -> Tuple[bool, float]:
    """
    Detect screen/moire patterns via frequency domain analysis.

    A photo-of-a-screen will have characteristic high-frequency horizontal bands
    that differ from a natural face photo.

    Returns:
        (passed, energy_ratio)  — passed=True means NO screen artifacts detected
    """
    img = _bytes_to_bgr(image_bytes)
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float64)

    # DFT
    f = np.fft.fft2(grey)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)
    h, w = grey.shape
    cy, cx = h // 2, w // 2

    # Radial mask: outer ring = high frequency
    Y, X = np.ogrid[:h, :w]
    radius = min(h, w) // 2
    outer_mask = ((X - cx) ** 2 + (Y - cy) ** 2) > (radius * 0.55) ** 2
    inner_mask = ((X - cx) ** 2 + (Y - cy) ** 2) < (radius * 0.25) ** 2

    outer_energy = float(np.mean(magnitude[outer_mask])) if np.any(outer_mask) else 0.0
    inner_energy = float(np.mean(magnitude[inner_mask])) if np.any(inner_mask) else 1.0

    ratio = outer_energy / max(inner_energy, 1e-6)
    passed = ratio < SCREEN_ARTIFACT_THRESHOLD
    return passed, ratio


def _embedding_variance(embeddings: List[np.ndarray]) -> float:
    """
    Compute variance across a set of face embeddings.

    If the variance is very low, the images are nearly identical —
    suggesting a static photo was presented multiple times (spoof).
    """
    if len(embeddings) < 2:
        return 1.0  # can't assess, assume live

    vecs = np.array(embeddings, dtype=np.float64)
    mean = vecs.mean(axis=0)
    # cosine similarity variance
    sims = []
    for v in vecs:
        denom = (np.linalg.norm(v) * np.linalg.norm(mean))
        if denom > 0:
            sims.append(float(np.dot(v, mean) / denom))
    if not sims:
        return 1.0
    return float(np.var(sims))


def check_liveness(
    image_bytes: bytes,
    previous_embeddings: Optional[List[np.ndarray]] = None,
    face_bbox=None,
) -> Tuple[bool, str]:
    """
    Multi-signal liveness check.

    Checks:
      1. Screen artifact detection (frequency domain)
      2. Cross-image embedding variance (if previous images provided)

    Returns:
        (passed, message)
    """
    issues = []

    # Check 1: screen artifacts
    screen_ok, ratio = _detect_screen_artifacts(image_bytes)
    if not screen_ok:
        issues.append(
            f"Possible screen/printed photo detected (artifact ratio: {ratio:.3f}, "
            f"threshold: {SCREEN_ARTIFACT_THRESHOLD})"
        )

    # Check 2: embedding variance across captures
    if previous_embeddings and len(previous_embeddings) >= 1:
        variance = _embedding_variance(previous_embeddings)
        if variance < VARIANCE_THRESHOLD:
            issues.append(
                f"Captive attack detected — images are too similar "
                f"(variance: {variance:.6f}, need ≥{VARIANCE_THRESHOLD})"
            )

    passed = len(issues) == 0
    msg = "Liveness check passed" if passed else "; ".join(issues)
    return passed, msg


# ---------------------------------------------------------------------------
# Step 6 — Composite quality gate
# ---------------------------------------------------------------------------

def compute_quality_score(
    blur_score: float,
    brightness: float,
    contrast: float,
    liveness_passed: bool,
    face_size_ratio: float = 0.0,
) -> float:
    """
    Compute a 0–100 quality score from individual metric scores.

    Each sub-score is normalized to 0–1, then weighted.
    """
    # Blur sub-score: sigmoid-like mapping around threshold
    blur_norm = min(blur_score / (BLUR_THRESHOLD * 2), 1.0)

    # Brightness sub-score: 1.0 at ideal (120), falls off toward extremes
    bdiff = abs(brightness - 120) / 120
    brightness_norm = max(0.0, 1.0 - bdiff)

    # Contrast sub-score
    contrast_norm = min(contrast / (CONTRAST_MIN * 2), 1.0)

    # Liveness sub-score: binary
    liveness_norm = 1.0 if liveness_passed else 0.0

    # Face size sub-score: 1.0 at ideal (0.35), falls off toward extremes
    # Ideal face size is around 35% of image area
    ideal_ratio = 0.35
    size_diff = abs(face_size_ratio - ideal_ratio) / ideal_ratio
    face_size_norm = max(0.0, 1.0 - size_diff)

    score = (
        QUALITY_WEIGHTS["blur"] * blur_norm
        + QUALITY_WEIGHTS["brightness"] * brightness_norm
        + QUALITY_WEIGHTS["contrast"] * contrast_norm
        + QUALITY_WEIGHTS["liveness"] * liveness_norm
        + QUALITY_WEIGHTS["face_size"] * face_size_norm
    ) * 100

    return round(score, 1)


def quality_gate(
    image_bytes: bytes,
    previous_embeddings: Optional[List[np.ndarray]] = None,
    face_bbox=None,
) -> Tuple[bool, dict]:
    """
    Run all quality checks and return a composite result.

    Returns:
        (passed, result_dict)
        result_dict has keys: blur, brightness, contrast, liveness, face_size, score, messages
    """
    messages = []

    # Blur
    blur_ok, blur_val, blur_msg = detect_blur(image_bytes, face_bbox)
    messages.append(blur_msg)

    # Brightness / contrast
    bright_ok, brightness, contrast, bright_msg = assess_brightness_contrast(image_bytes, face_bbox)
    messages.append(bright_msg)

    # Face size
    size_ok, size_ratio, size_msg = check_face_size(image_bytes, face_bbox)
    messages.append(size_msg)

    # Liveness
    live_ok, live_msg = check_liveness(image_bytes, previous_embeddings, face_bbox)
    messages.append(live_msg)

    # Composite score
    score = compute_quality_score(blur_val, brightness, contrast, live_ok, size_ratio)

    # Gate: all individual checks must pass AND score ≥ 50
    passed = blur_ok and bright_ok and size_ok and live_ok and score >= 50

    return passed, {
        "blur": {"passed": blur_ok, "value": blur_val},
        "brightness": {"passed": bright_ok, "value": brightness},
        "contrast": {"passed": bright_ok, "value": contrast},
        "face_size": {"passed": size_ok, "value": size_ratio},
        "liveness": {"passed": live_ok},
        "score": score,
        "messages": messages,
    }
