import time
from concurrent.futures import ThreadPoolExecutor
import logging

from ocr.preprocessing import preprocess_image

logger = logging.getLogger("legalcheck.ocr")

# Lazy initialize RapidOCR engine to speed up startup
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR engine initialized successfully.")
        except Exception as err:
            logger.warning(f"Failed to initialize RapidOCR engine: {err}. Falling back to pytesseract if available.")
            _ocr_engine = "tesseract_fallback"
    return _ocr_engine


def perform_ocr_single(image_bytes: bytes, image_index: int = 1) -> dict:
    """
    Runs OpenCV preprocessing and local OCR on a single image.
    
    Returns dict formatted:
    {
        "image_index": 1,
        "text": "...",
        "confidence": 0.92,
        "lines": [...],
        "line_count": 10
    }
    """
    start_time = time.time()
    processed_img, orig_img = preprocess_image(image_bytes)

    ocr_engine = get_ocr_engine()
    lines_detail = []
    text_lines = []
    total_conf = 0.0

    if ocr_engine != "tesseract_fallback" and ocr_engine is not None:
        try:
            results, elapse = ocr_engine(processed_img)
            if results:
                for item in results:
                    # RapidOCR returns: [bbox, text, confidence]
                    bbox = item[0]
                    txt = str(item[1]).strip()
                    try:
                        conf = float(item[2])
                    except (TypeError, ValueError):
                        conf = 0.80

                    if txt:
                        # Convert bbox numpy array to list if needed
                        bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else bbox
                        lines_detail.append({
                            "text": txt,
                            "confidence": round(conf, 3),
                            "bounding_box": bbox_list
                        })
                        text_lines.append(txt)
                        total_conf += conf
        except Exception as err:
            logger.error(f"RapidOCR execution failed on Image {image_index}: {err}")

    # Fallback to pytesseract if RapidOCR returned nothing or failed
    if not text_lines:
        try:
            import pytesseract
            from PIL import Image
            import io

            pil_img = Image.open(io.BytesIO(image_bytes))
            raw_txt = pytesseract.image_to_string(pil_img)
            lines = [line.strip() for line in raw_txt.splitlines() if line.strip()]
            for line in lines:
                lines_detail.append({
                    "text": line,
                    "confidence": 0.75,
                    "bounding_box": None
                })
                text_lines.append(line)
                total_conf += 0.75
        except Exception as py_err:
            logger.warning(f"PyTesseract fallback also failed or not installed: {py_err}")

    # Remove consecutive duplicate lines
    dedup_lines = []
    for line in text_lines:
        if not dedup_lines or dedup_lines[-1].lower() != line.lower():
            dedup_lines.append(line)

    full_text = "\n".join(dedup_lines)
    avg_conf = round(total_conf / len(lines_detail), 3) if lines_detail else 0.0
    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "image_index": image_index,
        "text": full_text,
        "confidence": avg_conf,
        "lines": lines_detail,
        "line_count": len(dedup_lines),
        "elapsed_ms": elapsed_ms
    }


def perform_ocr_multiple(images_bytes_list: list[bytes]) -> dict:
    """
    Performs OCR on multiple package images concurrently.
    Preserves image indexes and combines OCR text.
    """
    start_time = time.time()
    if not images_bytes_list:
        return {
            "combined_text": "",
            "per_image_results": [],
            "total_images": 0,
            "total_ocr_ms": 0
        }

    # Process images concurrently using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(4, len(images_bytes_list))) as executor:
        futures = [
            executor.submit(perform_ocr_single, img_bytes, idx + 1)
            for idx, img_bytes in enumerate(images_bytes_list)
        ]
        results = [f.result() for f in futures]

    # Sort by image_index to maintain order
    results.sort(key=lambda x: x["image_index"])

    combined_blocks = []
    for res in results:
        img_idx = res["image_index"]
        txt = res["text"].strip()
        if txt:
            combined_blocks.append(f"[Image {img_idx}]\n{txt}")
        else:
            combined_blocks.append(f"[Image {img_idx}]\n(No legible text detected by OCR)")

    combined_text = "\n\n".join(combined_blocks)
    total_ocr_ms = int((time.time() - start_time) * 1000)

    return {
        "combined_text": combined_text,
        "per_image_results": results,
        "total_images": len(images_bytes_list),
        "total_ocr_ms": total_ocr_ms
    }