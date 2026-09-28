from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.gemini_service import analyze_ocr_text, analyze_web_content
from ocr.preprocessing import preprocess_image
from ocr.ocr_service import extract_ocr_from_bytes, combine_multi_image_ocr
from rules_engine.compliance import check_compliance
from reporting.report import build_inspection_report
from web.web_service import fetch_and_extract_web_content


class URLInspectRequest(BaseModel):
    url: str


app = FastAPI(
    title="LegalCheck API",
    description=(
        "AI-assisted Legal Metrology "
        "compliance inspection system"
    ),
    version="0.3.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://legal-check-nu.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "project": "LegalCheck",
        "problem_id": "SIH26034",
        "pipeline": "OpenCV -> Local OCR -> Gemini Text-Only -> Rules Engine",
        "version": "0.3.0"
    }


@app.post("/inspect")
async def inspect_package(
    image: UploadFile = File(None),
    images: list[UploadFile] = File(None)
):
    """
    Inspect one or multiple package images using OpenCV preprocessing,
    local OCR extraction, combined text-only Gemini interpretation,
    and deterministic Legal Metrology compliance rules.
    """
    upload_list = []
    if images and len(images) > 0:
        upload_list = images
    elif image is not None:
        upload_list = [image]

    if not upload_list:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one package image."
        )

    processed_ocr_results = []
    filenames = []

    # 1. OpenCV Preprocessing & Local OCR per image
    for idx, img in enumerate(upload_list):
        if not img.content_type or not img.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"File {img.filename or idx + 1} is not a valid image."
            )

        raw_bytes = await img.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded image {img.filename or idx + 1} is empty."
            )

        fn = img.filename or f"package_photo_{idx + 1}.jpg"
        filenames.append(fn)

        # OpenCV Preprocessing
        prep_bytes, prep_meta = preprocess_image(raw_bytes)

        # Local OCR Extraction
        ocr_res = extract_ocr_from_bytes(
            image_bytes=prep_bytes,
            image_index=idx,
            filename=fn
        )
        processed_ocr_results.append(ocr_res)

    # 2. Combine OCR text across all uploaded package images
    combined_ocr = combine_multi_image_ocr(processed_ocr_results)
    combined_text = combined_ocr.get("combined_text", "").strip()

    if not combined_text:
        # Fallback text if OCR found no readable characters
        combined_text = f"Package images provided ({', '.join(filenames)}), but no legible text was extracted by local OCR."

    # 3. Text-Only AI Extraction via Gemini
    try:
        extracted_data = analyze_ocr_text(combined_ocr_text=combined_text)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"AI OCR text extraction failed: {str(error)}"
        )

    # 4. Deterministic compliance analysis
    source_info = {
        "type": "file",
        "filenames": filenames,
        "image_count": len(filenames)
    }
    compliance_result = check_compliance(
        extracted_data,
        inspection_type="package",
        source=source_info
    )

    # 5. Build explainable report
    report = build_inspection_report(
        extracted_data=extracted_data,
        compliance_result=compliance_result,
        inspection_type="package",
        source=source_info
    )

    report["file"] = {
        "filename": filenames[0] if filenames else "package.jpg",
        "filenames": filenames,
        "count": len(filenames)
    }

    # 6. Add development/debug OCR evidence metadata
    report["ocr_debug"] = {
        "images_processed": len(upload_list),
        "ocr_completed": True,
        "gemini_text_only": True,
        "average_confidence": combined_ocr.get("average_confidence", 0.0),
        "total_words": combined_ocr.get("total_words", 0),
        "combined_text": combined_text,
        "evidence": [
            {
                "image_index": res.get("image_index", i),
                "filename": res.get("filename", f"image_{i+1}.jpg"),
                "confidence": res.get("avg_confidence", 0.0),
                "words": res.get("total_words", 0),
                "text": res.get("combined_text", "")
            }
            for i, res in enumerate(processed_ocr_results)
        ]
    }

    report["project"] = "LegalCheck"
    report["problem_id"] = "SIH26034"

    return report


@app.post("/inspect-url")
async def inspect_url(payload: URLInspectRequest):
    url = payload.url.strip() if payload and payload.url else ""
    if not url:
        raise HTTPException(status_code=400, detail="Please provide a valid product URL.")

    # 1. Fetch & extract web page content
    web_res = fetch_and_extract_web_content(url)

    source = {
        "type": "web",
        "url": url,
        "domain": web_res.get("domain", ""),
        "page_title": web_res.get("page_title", "")
    }

    if not web_res.get("success"):
        reason = web_res.get("reason")
        err_msg = web_res.get("message", "Could not extract webpage content.")

        if reason == "security_error":
            raise HTTPException(status_code=400, detail=err_msg)

        empty_data = {
            "product_name": web_res.get("page_title") or None,
            "manufacturer": None,
            "manufactured_for": None,
            "net_quantity": None,
            "unit_sale_price": None,
            "mrp": None,
            "manufacturing_date": None,
            "best_before": None,
            "use_by": None,
            "expiry": None,
            "shelf_life": None,
            "country_of_origin": None,
            "consumer_care": None,
            "product_category": "other",
            "category_confidence": 0.0,
            "category_evidence": [],
            "package_type": "unknown",
            "is_imported": None,
            "has_shelf_life": None,
        }

        compliance_result = check_compliance(empty_data, inspection_type="digital", source=source)
        compliance_result["status"] = "requires_human_verification"

        report = build_inspection_report(
            extracted_data=empty_data,
            compliance_result=compliance_result,
            inspection_type="digital",
            source=source
        )
        report["verification"]["status"] = "requires_human_verification"
        report["verification"]["message"] = err_msg
        report["project"] = "LegalCheck"
        report["problem_id"] = "SIH26034"
        return report

    # 2. AI Extraction from extracted text & JSON-LD
    try:
        extracted_data = analyze_web_content(
            extracted_text=web_res.get("extracted_text", ""),
            json_ld=web_res.get("json_ld"),
            page_title=web_res.get("page_title")
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"AI web extraction failed: {str(error)}"
        )

    # 3. Deterministic compliance analysis
    compliance_result = check_compliance(extracted_data, inspection_type="digital", source=source)

    # 4. Build explainable report
    report = build_inspection_report(
        extracted_data=extracted_data,
        compliance_result=compliance_result,
        inspection_type="digital",
        source=source
    )

    report["project"] = "LegalCheck"
    report["problem_id"] = "SIH26034"

    return report