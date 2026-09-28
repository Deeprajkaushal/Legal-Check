import cv2
import numpy as np


def preprocess_image(image_bytes: bytes) -> tuple[np.ndarray, np.ndarray]:
    """
    Preprocess image for OCR using OpenCV.
    Enhances contrast, reduces noise, sharpens text while preserving legibility.
    
    Returns:
        (processed_bgr, original_bgr)
    """
    if not image_bytes:
        raise ValueError("Image byte buffer is empty.")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img_orig = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_orig is None:
        raise ValueError("Failed to decode image using OpenCV.")

    h, w = img_orig.shape[:2]

    # Target dimensions: Max side 2048px, Min side 600px
    max_dim = 2048
    min_dim = 600

    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
    elif min(h, w) < min_dim:
        scale = min_dim / min(h, w)

    if scale != 1.0:
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        interpolation = cv2.INTER_CUBIC if scale > 1.0 else cv2.INTER_AREA
        img_resized = cv2.resize(img_orig, (new_w, new_h), interpolation=interpolation)
    else:
        img_resized = img_orig.copy()

    # 1. Grayscale
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)

    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 3. Mild Denoising
    denoised = cv2.fastNlMeansDenoising(enhanced, None, h=5, templateWindowSize=7, searchWindowSize=21)

    # 4. Sharpening filter
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv2.filter2D(denoised, -1, kernel)

    # Convert back to 3-channel BGR image as expected by OCR engines
    processed_bgr = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    return processed_bgr, img_orig
