import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_FALLBACKS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.8-flash",
]

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured. Add it to backend/.env."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

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

EXTRACTION_OCR_PROMPT = """
You are the package-information extraction component of LegalCheck, an AI-assisted packaged-commodity Legal Metrology screening system for India.

You will receive EXTRACTED OCR TEXT from package photo(s).

CRITICAL OCR INTERPRETATION RULES:
1. The input is raw text extracted via OCR. It may contain spelling errors, duplicated lines, broken words, or OCR character substitutions (e.g., '0' vs 'O', '1' vs 'I').
2. Interpret the text conservatively based ONLY on visible OCR evidence.
3. Do NOT invent, assume, or calculate missing values.
4. If a field is not supported by the OCR text, return null.

DATE MAPPING RULES (CRITICAL):
- Labeled Mfg / Packing Date (e.g. "Pkg Date", "Packing Date", "Mfg Date", "Date of Packing", "Pkd Date") MUST be mapped to "manufacturing_date" or "packing_date". NEVER map a manufacturing/packing date to expiry or best_before!
- Labeled Expiry / Use By / Best Before Date (e.g. "Expiry Date", "Exp Date", "Use By", "Best Before", "EXP", "Use By Date") MUST be mapped to "expiry", "use_by", or "best_before".
- Example: "Pkg. Date: 05/2026, Expiry: 10/2027" -> manufacturing_date = "05/2026", expiry = "10/2027".
- Do NOT simply assign the first detected date to expiry or best_before.

COUNTRY OF ORIGIN RULES (CRITICAL):
- Do NOT set country_of_origin = "India" (or any country) simply because a country name appears inside a manufacturer address, company address, or consumer care postal address.
- Populate country_of_origin ONLY when an explicit origin declaration prefix is present in the OCR text, such as: "Made in [Country]", "Product of [Country]", "Country of Origin: [Country]", "Country of Manufacture: [Country]", "Country of Assembly: [Country]".
- If no explicit origin declaration is present, set country_of_origin = null.
- Set is_imported = true ONLY if explicit foreign origin or import text (e.g. "Made in China", "Product of USA", "Imported by", "Country of Origin: Japan") is present.
- Set is_imported = false ONLY if explicit domestic origin text (e.g. "Made in India", "Product of India", "Country of Origin: India") is present.
- Otherwise set is_imported = null.

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

Return valid JSON only. Do not include markdown fences or commentary.
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
        raise ValueError(
            f"Gemini returned invalid JSON: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object.")

    return data


def _normalise_extraction(data: dict, raw_ocr_text: str = "") -> dict:
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

    # Strict Country of Origin Enforcement:
    # Do NOT accept country_of_origin if it's based purely on company address
    if result["country_of_origin"] and raw_ocr_text:
        explicit_origin_pattern = re.compile(
            r'\b(made in|product of|country of origin|country of manufacture|country of assembly|origin\s*:)\b',
            re.IGNORECASE
        )
        if not explicit_origin_pattern.search(raw_ocr_text):
            # Country of Origin is NOT explicitly declared on package
            result["country_of_origin"] = None
            if result["is_imported"] is False:
                # Reset domestic assumption if only address was present
                result["is_imported"] = None

    # Handle shelf_life normalization & date separation
    mfg_date = result.get("manufacturing_date") or result.get("packing_date")
    exp_date = result.get("expiry") or result.get("use_by") or result.get("best_before")

    # Guard: If manufacturing_date and expiry are accidentally assigned identical values without expiry label
    if mfg_date and exp_date and mfg_date == exp_date:
        if raw_ocr_text and not re.search(r'\b(exp|expiry|best before|use by)\b', raw_ocr_text, re.IGNORECASE):
            result["expiry"] = None
            result["best_before"] = None
            result["use_by"] = None

    shelf_life_data = result.get("shelf_life")
    if isinstance(shelf_life_data, dict):
        raw_txt = shelf_life_data.get("raw_text") or shelf_life_data.get("value")
        sl_type = shelf_life_data.get("type", "unknown")
        result["shelf_life"] = {
            "value": shelf_life_data.get("value") or raw_txt,
            "type": sl_type if sl_type in ("best_before", "use_by", "expiry", "unknown") else "unknown",
            "raw_text": raw_txt,
        }
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


def analyze_ocr_text(combined_ocr_text: str) -> dict:
    """
    Pass COMBINED OCR TEXT to Gemini TEXT-ONLY model.
    Gemini receives TEXT, NOT the original image!
    """
    if not combined_ocr_text or not combined_ocr_text.strip():
        raise ValueError("Combined OCR text is empty.")

    full_prompt = (
        "Extracted OCR text from package image(s):\n\n"
        f"{combined_ocr_text}\n\n"
        "Interpret this OCR text and return the LegalCheck structured product schema."
    )

    last_error = None

    for model_name in MODEL_FALLBACKS:
        try:
            # TEXT ONLY CALL TO GEMINI: contents is a list of text strings ONLY!
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    EXTRACTION_OCR_PROMPT,
                    full_prompt,
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )

            response_text = response.text
            if not response_text:
                raise ValueError("Gemini returned an empty response.")

            extracted_data = _parse_json_response(response_text)
            return _normalise_extraction(extracted_data, raw_ocr_text=combined_ocr_text)

        except Exception as err:
            last_error = err
            err_str = str(err)
            if "503" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                time.sleep(1)
                continue
            continue

    raise RuntimeError(
        f"AI OCR text extraction failed across models: {str(last_error)}"
    )


def analyze_package_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    DEPRECATED DIRECT IMAGE PATH - Retained for backward compatibility.
    Primary inspection path uses analyze_ocr_text() with OpenCV + OCR text.
    """
    from ocr.preprocessing import preprocess_image
    from ocr.ocr_service import extract_ocr_from_bytes

    prep_bytes, _ = preprocess_image(image_bytes)
    ocr_res = extract_ocr_from_bytes(prep_bytes, image_index=0)
    ocr_text = ocr_res.get("combined_text", "")

    if ocr_text:
        return analyze_ocr_text(ocr_text)

    # Emergency fallback to direct image if OCR returned absolutely nothing
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    last_error = None
    for model_name in MODEL_FALLBACKS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[EXTRACTION_OCR_PROMPT, image_part],
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
            )
            return _normalise_extraction(_parse_json_response(response.text))
        except Exception as err:
            last_error = err
            continue
    raise RuntimeError(f"Fallback extraction failed: {str(last_error)}")


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

    for model_name in MODEL_FALLBACKS:
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
            if not response_text:
                raise ValueError("Gemini returned an empty response.")

            extracted_data = _parse_json_response(response_text)
            return _normalise_extraction(extracted_data, raw_ocr_text=full_text_input)

        except Exception as err:
            last_error = err
            err_str = str(err)
            if "503" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                time.sleep(1)
                continue
            continue

    raise RuntimeError(
        f"AI web extraction failed across models: {str(last_error)}"
    )
