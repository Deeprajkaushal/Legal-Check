import json
import os
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

EXTRACTION_PROMPT = """
You are the package-information extraction component of LegalCheck,
an AI-assisted packaged-commodity Legal Metrology screening system for India.

Your job is ONLY to inspect the supplied package image and extract information
that is visibly printed on the package. Do NOT decide whether the package is
legally compliant. Do NOT invent missing information. Do NOT calculate values
that are not explicitly printed.

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

Extraction & Classification Rules:

1. Read only information that is visible or reasonably legible in the image.
2. If a field is not visible or cannot be reliably read, return null.
3. Preserve the printed wording/value as closely as possible.
4. For shelf_life, recognize labels such as "Best Before", "Best Before Date", "Use By", "Use By Date", "Expiry", "Expiry Date", "Expires", "Expiration Date".
   Preserve exact detected wording in raw_text. Do not invent a date.
5. For MRP and Unit Sale Price: They are legally distinct. Extract MRP exactly as visible. Extract Unit Sale Price ONLY when explicitly printed as a price per unit/g/ml/kg/L. Never calculate Unit Sale Price from MRP and quantity.
6. For is_imported: Set to true ONLY when explicit import evidence is visible (e.g., "Made in [foreign country]", "Product of [foreign country]", "Imported by", "Country of Origin [foreign country]").
   Set to false ONLY when explicit domestic evidence is visible (e.g., "Made in India", "Manufactured in India").
   If evidence is insufficient or country of origin text is not found, return is_imported = null (DO NOT assume false).
7. For has_shelf_life: true when best-before/use-by/expiry declaration is visible or applicable to the commodity type.
8. Return valid JSON only. Do not include markdown fences or commentary.
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


def _normalise_extraction(data: dict) -> dict:
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
        if not result["best_before"]:
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


def analyze_package_image(
    image_bytes: bytes,
    mime_type: str,
) -> dict:
    if not image_bytes:
        raise ValueError("Image data is empty.")

    if not mime_type.startswith("image/"):
        raise ValueError("The uploaded file must be an image.")

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    last_error = None

    for model_name in MODEL_FALLBACKS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    EXTRACTION_PROMPT,
                    image_part,
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
            return _normalise_extraction(extracted_data)

        except Exception as err:
            last_error = err
            err_str = str(err)
            if "503" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                time.sleep(1)
                continue
            continue

    raise RuntimeError(
        f"AI extraction failed across models: {str(last_error)}"
    )


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
            return _normalise_extraction(extracted_data)

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

