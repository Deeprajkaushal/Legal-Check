import io
import os
import re
from PIL import Image

# Initialize RapidOCR engine lazily
_rapid_ocr_engine = None


def _get_ocr_engine():
    global _rapid_ocr_engine
    if _rapid_ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapid_ocr_engine = RapidOCR()
        except ImportError:
            _rapid_ocr_engine = False
    return _rapid_ocr_engine


def extract_ocr_from_bytes(
    image_bytes: bytes,
    image_index: int = 0,
    filename: str = ""
) -> dict:
    """
    Run local OCR on image bytes.

    Returns:
        {
          "image_index": 0,
          "filename": "front.jpg",
          "items": [
            {
              "image_index": 0,
              "text": "...",
              "confidence": 0.92,
              "bounding_box": [x1, y1, x2, y2]
            }
          ],
          "combined_text": "...",
          "avg_confidence": 0.92,
          "total_words": 45
        }
    """
    if not image_bytes:
        return {
            "image_index": image_index,
            "filename": filename,
            "items": [],
            "combined_text": "",
            "avg_confidence": 0.0,
            "total_words": 0,
            "error": "Empty image bytes"
        }

    ocr_items = []
    engine = _get_ocr_engine()

    # Try RapidOCR first
    if engine:
        try:
            # RapidOCR can accept image bytes directly or numpy array or PIL image
            res, _ = engine(image_bytes)
            if res:
                for box, text, score in res:
                    text_str = str(text).strip()
                    if not text_str:
                        continue

                    # box is polygon points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    try:
                        xs = [p[0] for p in box]
                        ys = [p[1] for p in box]
                        bbox = [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]
                    except Exception:
                        bbox = [0, 0, 0, 0]

                    conf = round(float(score), 4) if score is not None else 0.0

                    ocr_items.append({
                        "image_index": image_index,
                        "text": text_str,
                        "confidence": conf,
                        "bounding_box": bbox
                    })
        except Exception as err:
            ocr_items = []

    # Fallback to Pytesseract if RapidOCR failed or produced no results
    if not ocr_items:
        try:
            import pytesseract

            # Set tesseract path on Windows if default executable exists
            tess_win = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.exists(tess_win):
                pytesseract.pytesseract.tesseract_cmd = tess_win

            pil_img = Image.open(io.BytesIO(image_bytes))
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)

            n_boxes = len(data.get("text", []))
            for i in range(n_boxes):
                t_str = str(data["text"][i]).strip()
                conf_val = data["conf"][i]
                if t_str and conf_val != -1 and conf_val != "-1":
                    c_float = round(float(conf_val) / 100.0, 4)
                    x = data["left"][i]
                    y = data["top"][i]
                    w = data["width"][i]
                    h = data["height"][i]
                    ocr_items.append({
                        "image_index": image_index,
                        "text": t_str,
                        "confidence": c_float,
                        "bounding_box": [x, y, x + w, y + h]
                    })
        except Exception:
            pass

    # Deduplicate consecutive identical text lines per image
    seen_lines = set()
    cleaned_lines = []
    for item in ocr_items:
        t = item["text"]
        normalized = re.sub(r'\s+', ' ', t).lower()
        if normalized not in seen_lines:
            seen_lines.add(normalized)
            cleaned_lines.append(t)

    combined_text = "\n".join(cleaned_lines)
    avg_conf = (
        round(sum(item["confidence"] for item in ocr_items) / len(ocr_items), 4)
        if ocr_items else 0.0
    )

    return {
        "image_index": image_index,
        "filename": filename or f"image_{image_index + 1}.jpg",
        "items": ocr_items,
        "combined_text": combined_text,
        "avg_confidence": avg_conf,
        "total_words": len(cleaned_lines)
    }


def combine_multi_image_ocr(ocr_results_list: list[dict]) -> dict:
    """
    Combine OCR text from multiple package images into a single structured prompt input.
    Format:
    [Image 1: front.jpg]
    ...
    [Image 2: back.jpg]
    ...
    """
    formatted_parts = []
    all_items = []
    total_words = 0
    total_conf = 0.0
    valid_counts = 0

    for idx, res in enumerate(ocr_results_list):
        img_idx = res.get("image_index", idx)
        fn = res.get("filename", f"image_{img_idx + 1}.jpg")
        text = res.get("combined_text", "").strip()

        formatted_parts.append(f"[Image {img_idx + 1}: {fn}]\n{text if text else '(No text detected)'}")
        all_items.extend(res.get("items", []))

        w_cnt = res.get("total_words", 0)
        total_words += w_cnt

        if res.get("avg_confidence", 0) > 0:
            total_conf += res["avg_confidence"]
            valid_counts += 1

    overall_text = "\n\n".join(formatted_parts)
    overall_avg_conf = round(total_conf / valid_counts, 4) if valid_counts > 0 else 0.0

    return {
        "image_count": len(ocr_results_list),
        "combined_text": overall_text,
        "all_items": all_items,
        "total_words": total_words,
        "average_confidence": overall_avg_conf,
        "per_image": ocr_results_list
    }