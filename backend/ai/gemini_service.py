import json
import os
import re
import time
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("legalcheck.ai")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_FALLBACKS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
]

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

ALLOWED_CATEGORIES = {
    "packaged_food",
    "beverage",
    "cosmetic",
    "personal_care",
    "household_product",
    "pan_masala",
    "other",
}

ALLOWED_PACKAGE_TYPES = {
    "single_package",
    "combination_package",
    "group_package",
    "multi_piece_package",
    "unknown",
}

OCR_EXTRACTION_PROMPT = """
You are the OCR text interpretation component of LegalCheck, an AI-assisted packaged-commodity Legal Metrology screening system for India.

Your job is ONLY to inspect the provided raw OCR text extracted from package image(s) and extract the structured product declarations.

CRITICAL INSTRUCTIONS & CONSTRAINTS:
1. Do NOT invent or hallucinate information that is not supported by the OCR text.
2. If a field is not present or cannot be established from the OCR text, return null.
3. The raw OCR text may contain spelling errors, character substitutions, missing letters, mangled word boundaries, and out-of-order lines. Interpret the text conservatively.
4. DATE EXTRACTION RULES:
   - Differentiate strictly between Manufacturing/Packing Date and Expiry/Best Before/Use By Date.
   - Pkg Date / Packing Date / Mfg Date -> manufacturing_date or packing_date.
   - Expiry Date / Best Before / Use By -> expiry, best_before, or use_by.
   - Example: If OCR contains "Pkg. Date: 05/2026" and "Expiry: 10/2027", manufacturing_date MUST be "05/2026" and expiry MUST be "10/2027". NEVER map Pkg Date to Expiry!
5. COUNTRY OF ORIGIN & IMPORTED STATUS RULES:
   - Do NOT infer country_of_origin = "India" merely because "India" appears in a manufacturer/company address or consumer care address (e.g. "Mumbai, India").
   - Only set country_of_origin when explicit origin wording is present (e.g. "Made in India", "Product of India", "Country of Origin: India", "Country of Manufacture: India", "Country of Assembly: India").
   - For is_imported: Set to true ONLY if explicit import declaration is present (e.g., "Made in China", "Imported by...", "Country of Origin: Germany"). Set to false ONLY if explicit domestic manufacturing declaration is present (e.g. "Made in India", "Product of India"). Otherwise return null.

Return exactly one JSON object with these fields:

{
  "product_name": string | null,
  "manufacturer": string | null,
  "packer": string | null,
  "importer": string | null,
  "manufactured_for": string | null,
  "net_quantity": string | null,
  "unit_sale_price": string | null,
  "mrp": string | null,
  "manufacturing_date": string | null,
  "packing_date": string | null,
  "import_date": string | null,
  "best_before": string | null,
  "use_by": string | null,
  "expiry": string | null,
  "shelf_life": {
    "value": string | null,
    "type": "best_before" | "use_by" | "expiry" | "unknown" | null,
    "raw_text": string | null
  } | null,
  "country_of_origin": string | null,
  "consumer_care": string | null,
  "product_category": string | null,
  "category_confidence": number | null,
  "category_evidence": [string] | null,
  "package_type": "single_package" | "combination_package" | "group_package" | "multi_piece_package" | "unknown" | null,
  "is_imported": boolean | null,
  "has_shelf_life": boolean | null
}

Allowed product_category values:
- packaged_food
- beverage
- cosmetic
- personal_care
- household_product
- pan_masala
- other

Package Type Rules:
- combination_package: A package containing two or more different commodities.
- group_package: A package containing two or more similar but non-identical items.
- multi_piece_package: A package containing multiple identical individually packaged/labelled pieces of the same commodity.
- single_package: A standard individual package containing a single item/quantity.
- unknown: Use when evidence is uncertain or insufficient.
"""

REQUIRED_FIELDS = {
    "product_name": None,
    "manufacturer": None,
    "packer": None,
    "importer": None,
    "manufactured_for": None,
    "net_quantity": None,
    "unit_sale_price": None,
    "mrp": None,
    "manufacturing_date": None,
    "packing_date": None,
    "import_date": None,
    "best_before": None,
    "use_by": None,
    "expiry": None,
    "shelf_life": None,
    "country_of_origin": None,
    "consumer_care": None,
    "product_category": None,
    "category_confidence": None,
    "category_evidence": [],
    "package_type": "unknown",
    "is_imported": None,
    "has_shelf_life": None,
}


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError(f"Gemini returned invalid JSON: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object.")

    return data


def _normalise_extraction(data: dict, ocr_text: str = "") -> dict:
    result = {}

    for field, default in REQUIRED_FIELDS.items():
        result[field] = data.get(field, default)

    category = result["product_category"]
    if category not in ALLOWED_CATEGORIES:
        result["product_category"] = "other" if category else None

    pkg_type = result["package_type"]
    if pkg_type not in ALLOWED_PACKAGE_TYPES:
        result["package_type"] = "unknown"

    confidence = result["category_confidence"]
    if confidence is not None:
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = None
    result["category_confidence"] = confidence

    # -------------------------------------------------------------
    # DATE EXTRACTION BUG FIX: Strict date verification against OCR text
    # -------------------------------------------------------------
    if ocr_text:
        ocr_lower = ocr_text.lower()
        
        mfg_match = re.search(r'(?:pkg|mfg|pack|manufactur\w*)\.?\s*(?:date|d)?\s*[:\.-]?\s*([0-9]{1,2}[/\.-][0-9]{2,4}|[a-z]{3}\s*[0-9]{2,4})', ocr_lower)
        exp_match = re.search(r'(?:exp|expiry|use\s*by|best\s*before)\.?\s*(?:date|d)?\s*[:\.-]?\s*([0-9]{1,2}[/\.-][0-9]{2,4}|[a-z]{3}\s*[0-9]{2,4})', ocr_lower)

        if mfg_match:
            detected_mfg = mfg_match.group(1).upper()
            if not result["manufacturing_date"] and not result["packing_date"]:
                result["manufacturing_date"] = detected_mfg

        if exp_match:
            detected_exp = exp_match.group(1).upper()
            if not result["expiry"] and not result["best_before"] and not result["use_by"]:
                result["expiry"] = detected_exp

    # Handle shelf_life normalization
    shelf_life_data = result.get("shelf_life")
    if isinstance(shelf_life_data, dict):
        raw_txt = shelf_life_data.get("raw_text") or shelf_life_data.get("value")
        sl_type = shelf_life_data.get("type", "unknown")
        result["shelf_life"] = {
            "value": shelf_life_data.get("value") or raw_txt,
            "type": sl_type if sl_type in ("best_before", "use_by", "expiry", "unknown") else "unknown",
            "raw_text": raw_txt,
        }
        if not result["best_before"] and not result["expiry"]:
            if sl_type == "expiry":
                result["expiry"] = raw_txt
            else:
                result["best_before"] = raw_txt
    elif result.get("best_before") or result.get("use_by") or result.get("expiry"):
        raw_txt = result.get("best_before") or result.get("use_by") or result.get("expiry")
        sl_type = "best_before" if result.get("best_before") else ("use_by" if result.get("use_by") else "expiry")
        result["shelf_life"] = {
            "value": raw_txt,
            "type": sl_type,
            "raw_text": raw_txt,
        }

    # If shelf_life has a value, mark has_shelf_life = True
    if result["shelf_life"] and result["shelf_life"].get("raw_text"):
        result["has_shelf_life"] = True

    # -------------------------------------------------------------
    # COUNTRY OF ORIGIN FIX: Strict non-inference from address
    # -------------------------------------------------------------
    coo = result.get("country_of_origin")
    if coo:
        coo_str = str(coo).strip().lower()
        if ocr_text:
            ocr_lower = ocr_text.lower()
            has_explicit_marker = any(m in ocr_lower for m in [
                "made in", "product of", "country of origin", "country of manufacture", "country of assembly", "produced in", "imported from"
            ])
            if not has_explicit_marker and coo_str == "india":
                result["country_of_origin"] = None
                result["is_imported"] = None

    for field in ("is_imported", "has_shelf_life"):
        value = result[field]
        if value is not None and not isinstance(value, bool):
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered == "true":
                    result[field] = True
                elif lowered == "false":
                    result[field] = False
                else:
                    result[field] = None
            else:
                result[field] = None

    for field, value in result.items():
        if isinstance(value, str):
            result[field] = value.strip() or None

    return result


def _build_ocr_evidence(extracted_data: dict, per_image_ocr: list) -> list:
    evidence_items = []
    
    field_labels = {
        "product_name": "Product Name",
        "mrp": "Maximum Retail Price (MRP)",
        "net_quantity": "Net Quantity",
        "unit_sale_price": "Unit Sale Price",
        "manufacturer": "Manufacturer",
        "packer": "Packer",
        "importer": "Importer",
        "manufacturing_date": "Manufacturing / Packing Date",
        "packing_date": "Packing Date",
        "expiry": "Expiry Date",
        "best_before": "Best Before Date",
        "country_of_origin": "Country of Origin",
        "consumer_care": "Consumer Care Details"
    }

    if not per_image_ocr:
        for field, label in field_labels.items():
            val = extracted_data.get(field)
            if val:
                evidence_items.append({
                    "field": field,
                    "label": label,
                    "detected_value": str(val),
                    "source_image": "Image 1",
                    "ocr_snippet": str(val),
                    "confidence": 0.85,
                    "bounding_box": None
                })
        return evidence_items

    for field, label in field_labels.items():
        val = extracted_data.get(field)
        if not val:
            continue
        
        val_str = str(val).strip().lower()
        matched = False

        for img_res in per_image_ocr:
            img_idx = img_res.get("image_index", 1)
            lines = img_res.get("lines", [])

            for line_item in lines:
                line_txt = line_item.get("text", "")
                line_lower = line_txt.lower()

                if val_str in line_lower or (len(val_str) > 4 and val_str[:6] in line_lower):
                    evidence_items.append({
                        "field": field,
                        "label": label,
                        "detected_value": str(val),
                        "source_image": f"Image {img_idx}",
                        "ocr_snippet": line_txt,
                        "confidence": line_item.get("confidence", 0.90),
                        "bounding_box": line_item.get("bounding_box")
                    })
                    matched = True
                    break
            if matched:
                break

        if not matched:
            first_img_idx = per_image_ocr[0].get("image_index", 1) if per_image_ocr else 1
            avg_conf = per_image_ocr[0].get("confidence", 0.85) if per_image_ocr else 0.85
            evidence_items.append({
                "field": field,
                "label": label,
                "detected_value": str(val),
                "source_image": f"Image {first_img_idx}",
                "ocr_snippet": str(val),
                "confidence": avg_conf,
                "bounding_box": None
            })

    return evidence_items


def _fallback_extract_from_ocr_text(ocr_text: str) -> dict:
    """
    Fallback deterministic parser when Gemini API is rate limited (429) or unavailable (503).
    Extracts key package declarations directly from raw OCR text in ~1ms.
    """
    logger.info("Executing local OCR text fallback parser for LegalCheck declarations.")
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    
    product_name = None
    mrp = None
    net_qty = None
    mfg_date = None
    exp_date = None
    consumer_care = None
    country_of_origin = None
    
    for line in lines:
        line_lower = line.lower()
        
        # Product name heuristic
        if not product_name and len(line) > 3 and not any(k in line_lower for k in ["mrp", "pkg", "exp", "net", "mfg", "batch", "lic"]):
            product_name = line
            
        # MRP pattern
        mrp_match = re.search(r'(?:mrp|rs|₹|price)\.?\s*[:\.-]?\s*(?:rs\.?|₹)?\s*([0-9]+(?:\.[0-9]{2})?)', line_lower)
        if mrp_match and not mrp:
            mrp = f"₹{mrp_match.group(1)}"
            
        # Net Qty pattern
        qty_match = re.search(r'(?:net\s*(?:qty|quantity|wt|weight)|quantity)\.?\s*[:\.-]?\s*([0-9]+\s*(?:g|kg|ml|l|L|g\.?|N|u|units?))', line_lower)
        if qty_match and not net_qty:
            net_qty = qty_match.group(1)
            
        # Mfg / Pkg date pattern
        mfg_m = re.search(r'(?:pkg|mfg|pack|manufactur\w*)\.?\s*(?:date|d)?\s*[:\.-]?\s*([0-9]{1,2}[/\.-][0-9]{2,4}|[a-z]{3}\s*[0-9]{2,4})', line_lower)
        if mfg_m and not mfg_date:
            mfg_date = mfg_m.group(1).upper()
            
        # Expiry / Best before pattern
        exp_m = re.search(r'(?:exp|expiry|use\s*by|best\s*before)\.?\s*(?:date|d)?\s*[:\.-]?\s*([0-9]{1,2}[/\.-][0-9]{2,4}|[a-z]{3}\s*[0-9]{2,4})', line_lower)
        if exp_m and not exp_date:
            exp_date = exp_m.group(1).upper()

        # Explicit Country of Origin pattern
        coo_m = re.search(r'(?:made\s*in|product\s*of|country\s*of\s*origin|country\s*of\s*manufacture)\s*[:\.-]?\s*([a-zA-Z\s]+)', line_lower)
        if coo_m and not country_of_origin:
            country_of_origin = coo_m.group(1).strip().title()

    raw_data = {
        "product_name": product_name or "Packaged Commodity",
        "manufacturer": None,
        "packer": None,
        "importer": None,
        "manufactured_for": None,
        "net_quantity": net_qty,
        "unit_sale_price": None,
        "mrp": mrp,
        "manufacturing_date": mfg_date,
        "packing_date": mfg_date,
        "import_date": None,
        "best_before": exp_date,
        "use_by": None,
        "expiry": exp_date,
        "shelf_life": {"value": exp_date, "type": "best_before", "raw_text": exp_date} if exp_date else None,
        "country_of_origin": country_of_origin,
        "consumer_care": consumer_care,
        "product_category": "other",
        "category_confidence": 0.70,
        "category_evidence": ["Extracted via local OCR rule engine"],
        "package_type": "single_package",
        "is_imported": True if country_of_origin and "india" not in country_of_origin.lower() else None,
        "has_shelf_life": True if exp_date else None
    }
    
    return _normalise_extraction(raw_data, ocr_text)


def analyze_ocr_text(
    ocr_combined_text: str,
    per_image_ocr: list = None
) -> dict:
    """
    Interprets OCR text using Gemini TEXT-ONLY mode.
    Falls back immediately to local OCR text parser if Gemini API is rate-limited (429) or busy (503).
    """
    if not ocr_combined_text or not ocr_combined_text.strip():
        empty_data = _normalise_extraction({}, "")
        empty_data["ocr_evidence"] = []
        return empty_data

    user_prompt = f"Extracted OCR text from package images:\n\n{ocr_combined_text}\n\nInterpret this OCR text conservatively and return the LegalCheck structured product JSON object."

    start_time = time.time()
    last_error = None

    if client:
        for model_name in MODEL_FALLBACKS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        OCR_EXTRACTION_PROMPT,
                        user_prompt,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        http_options=types.HttpOptions(timeout=5.0),
                    ),
                )

                response_text = response.text
                if response_text:
                    raw_data = _parse_json_response(response_text)
                    normalized_data = _normalise_extraction(raw_data, ocr_combined_text)
                    normalized_data["ocr_evidence"] = _build_ocr_evidence(normalized_data, per_image_ocr or [])
                    normalized_data["gemini_time_ms"] = int((time.time() - start_time) * 1000)
                    return normalized_data

            except Exception as err:
                last_error = err
                logger.warning(f"Gemini model {model_name} failed: {err}")
                continue

    # Instant local OCR parser fallback (0.001s execution)
    logger.warning(f"Using local OCR fallback parser (Gemini API status: {last_error})")
    fallback_data = _fallback_extract_from_ocr_text(ocr_combined_text)
    fallback_data["ocr_evidence"] = _build_ocr_evidence(fallback_data, per_image_ocr or [])
    fallback_data["gemini_time_ms"] = int((time.time() - start_time) * 1000)
    return fallback_data


def analyze_package_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> dict:
    """
    Backward-compatible entry point for single image inspection.
    Uses OpenCV preprocessing + local OCR -> Gemini TEXT ONLY.
    """
    from ocr.ocr_service import perform_ocr_single

    ocr_res = perform_ocr_single(image_bytes, image_index=1)
    return analyze_ocr_text(ocr_res["text"], [ocr_res])


WEB_EXTRACTION_PROMPT = """
You are the product-information extraction component of LegalCheck, an AI-assisted packaged-commodity Legal Metrology screening system for India.

You are given text and metadata extracted from a public product webpage. Extract ONLY information directly supported by the supplied text. Do NOT infer or fabricate declarations. Do NOT decide whether the product is legally compliant. If a field cannot be established from the supplied text, return null.

Return exactly one JSON object with these fields:

{
  "product_name": string | null,
  "manufacturer": string | null,
  "packer": string | null,
  "importer": string | null,
  "manufactured_for": string | null,
  "net_quantity": string | null,
  "unit_sale_price": string | null,
  "mrp": string | null,
  "manufacturing_date": string | null,
  "packing_date": string | null,
  "import_date": string | null,
  "best_before": string | null,
  "use_by": string | null,
  "expiry": string | null,
  "shelf_life": {
    "value": string | null,
    "type": "best_before" | "use_by" | "expiry" | "unknown" | null,
    "raw_text": string | null
  } | null,
  "country_of_origin": string | null,
  "consumer_care": string | null,
  "product_category": string | null,
  "category_confidence": number | null,
  "category_evidence": [string] | null,
  "package_type": "single_package" | "combination_package" | "group_package" | "multi_piece_package" | "unknown" | null,
  "is_imported": boolean | null,
  "has_shelf_life": boolean | null
}

Allowed product_category values:
- packaged_food
- beverage
- cosmetic
- personal_care
- household_product
- pan_masala
- other

Package Type Rules:
- combination_package: A package containing two or more different commodities.
- group_package: A package containing two or more similar but non-identical items.
- multi_piece_package: A package containing multiple identical individually packaged/labelled pieces of the same commodity.
- single_package: A standard individual package containing a single item/quantity.
- unknown: Use when evidence is uncertain or insufficient.

Extraction Rules:
1. Extract only declarations explicitly stated in the webpage content or JSON-LD.
2. If a declaration is not present on the webpage, return null.
3. For shelf_life: preserve exact detected wording in raw_text. Do not invent a date.
4. For is_imported: Set to true ONLY when explicit import evidence is found (e.g., "Made in [foreign country]", "Imported by", "Country of Origin [foreign country]"). Set to false ONLY when explicit domestic evidence is found (e.g., "Made in India"). Otherwise return null.
5. Return valid JSON only. Do not include markdown fences or commentary.
"""


def analyze_web_content(
    extracted_text: str,
    json_ld: list | dict = None,
    page_title: str = None,
) -> dict:
    if not extracted_text and not json_ld:
        raise ValueError("Webpage text and JSON-LD are empty.")

    context_parts = []
    if page_title:
        context_parts.append(f"Webpage Title: {page_title}")
    if json_ld:
        context_parts.append(f"Structured JSON-LD Data:\n{json.dumps(json_ld, indent=2)}")
    if extracted_text:
        context_parts.append(f"Visible Text Content:\n{extracted_text}")

    full_text_input = "\n\n".join(context_parts)
    last_error = None

    if client:
        for model_name in ["gemini-3.6-flash", "gemini-flash-latest"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        WEB_EXTRACTION_PROMPT,
                        full_text_input,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                    ),
                )

                response_text = response.text
                if response_text:
                    extracted_data = _parse_json_response(response_text)
                    return _normalise_extraction(extracted_data, extracted_text)

            except Exception as err:
                last_error = err
                logger.warning(f"Web model {model_name} failed: {err}")
                break

    fallback_data = _fallback_extract_from_ocr_text(extracted_text)
    return fallback_data
