import cv2
import numpy as np


def preprocess_image(image_bytes: bytes) -> tuple[bytes, dict]:
    """
    Preprocess uploaded package image before passing to OCR.
    Lightweight, RAM-efficient OpenCV pipeline for cloud deployment.
    """
    if not image_bytes:
        return image_bytes, {"processed": False, "reason": "empty_bytes"}

    try:
        # 1. Decode bytes into OpenCV image matrix
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return image_bytes, {"processed": False, "reason": "invalid_image_format"}

        orig_h, orig_w = img.shape[:2]

        # 2. Downscale to max 1500px for high performance and low memory
        target_img = img
        scale_factor = 1.0

        if max(orig_h, orig_w) > 1500:
            scale_factor = 1500.0 / max(orig_h, orig_w)
            new_w = int(orig_w * scale_factor)
            new_h = int(orig_h * scale_factor)
            target_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 3. Grayscale conversion
        gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)

        # 4. Contrast enhancement via CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(gray)

        # 5. Fast Gaussian blur for noise suppression (RAM friendly)
        denoised = cv2.GaussianBlur(contrast_enhanced, (3, 3), 0)

        # 6. Sharpening filter
        kernel = np.array([
            [0, -0.5, 0],
            [-0.5, 3.0, -0.5],
            [0, -0.5, 0]
        ], dtype=np.float32)
        sharpened = cv2.filter2D(denoised, -1, kernel)

        # Encode back to PNG bytes
        success, encoded_img = cv2.imencode('.png', sharpened)
        if not success:
            return image_bytes, {"processed": False, "reason": "encode_failed"}

        processed_bytes = encoded_img.tobytes()

        metadata = {
            "processed": True,
            "original_dimensions": [orig_w, orig_h],
            "processed_dimensions": [sharpened.shape[1], sharpened.shape[0]],
            "scale_factor": round(scale_factor, 2),
            "steps": ["resize", "grayscale", "clahe_contrast", "gaussian_blur", "sharpening"]
        }

        return processed_bytes, metadata

    except Exception as err:
        # Fallback to original bytes if OpenCV processing encounters any error
        return image_bytes, {"processed": False, "error": str(err)}
