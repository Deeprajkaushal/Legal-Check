import time
import logging
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ocr.ocr_service import perform_ocr_multiple
from ai.gemini_service import analyze_ocr_text, analyze_web_content
from rules_engine.compliance import check_compliance
from reporting.report import build_inspection_report
from web.web_service import fetch_and_extract_web_content

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("legalcheck.main")


class URLInspectRequest(BaseModel):
    url: str


app = FastAPI(
    title="LegalCheck API",
    description=(
        "AI-assisted Legal Metrology "
        "compliance inspection system using OCR + Gemini Text-Only"
    ),
    version="0.3.2"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://legal-check-nu.vercel.app",
        "*"
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
        "version": "0.3.2",
        "ocr_pipeline": "OpenCV + RapidOCR + Gemini Text-Only"
    }


@app.post("/inspect")
async def inspect_package(
    request: Request,
    files: List[UploadFile] = File([]),
    images: List[UploadFile] = File([]),
    image: Optional[UploadFile] = File(None)
):
    total_start_time = time.time()
    uploaded_files: List[UploadFile] = []

    # Canonical Field: 'files'
    if files:
        if isinstance(files, list):
            uploaded_files.extend([f for f in files if isinstance(f, UploadFile) and f.filename])
        elif isinstance(files, UploadFile) and files.filename:
            uploaded_files.append(files)

    # Secondary Field: 'images'
    if not uploaded_files and images:
        if isinstance(images, list):
            uploaded_files.extend([f for f in images if isinstance(f, UploadFile) and f.filename])
        elif isinstance(images, UploadFile) and images.filename:
            uploaded_files.append(images)

    # Secondary Field: 'image'
    if not uploaded_files and image:
        if isinstance(image, UploadFile) and image.filename:
            uploaded_files.append(image)

    # Fallback to reading raw request.form() for any UploadFile regardless of field key name
    if not uploaded_files:
        try:
            form = await request.form()
            for key, val in form.multi_items():
                if isinstance(val, UploadFile) and val.filename:
                    uploaded_files.append(val)
        except Exception as form_err:
            logger.warning(f"Could not parse request.form(): {form_err}")

    logger.info(f"[INSPECT] Received {len(uploaded_files)} file(s): {[f.filename for f in uploaded_files]}")
    for f in uploaded_files:
        logger.info(f"[INSPECT] file={f.filename} type={f.content_type} size={getattr(f, 'size', 'unknown')}")

    if not uploaded_files:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one image file."
        )

    # 1. Read files into bytes
    images_bytes_list = []
    file_metadata = []

    for f in uploaded_files:
        if f.content_type and not f.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} is not a valid image."
            )
        content = await f.read()
        if not content:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file {f.filename} is empty."
            )
        images_bytes_list.append(content)
        file_metadata.append({
            "filename": f.filename or "package.jpg",
            "content_type": f.content_type or "image/jpeg",
            "size_bytes": len(content)
        })

    # 2. OpenCV Preprocessing & Local OCR (Concurrent)
    ocr_start = time.time()
    try:
        ocr_result = perform_ocr_multiple(images_bytes_list)
    except Exception as error:
        logger.error(f"OCR processing failed: {error}")
        raise HTTPException(
            status_code=500,
            detail=f"Image preprocessing or OCR failed: {str(error)}"
        )
    ocr_duration = time.time() - ocr_start

    combined_ocr_text = ocr_result.get("combined_text", "")
    per_image_ocr = ocr_result.get("per_image_results", [])

    # 3. Gemini TEXT-ONLY Extraction (with local OCR fallback if Gemini API is busy)
    gemini_start = time.time()
    try:
        extracted_data = analyze_ocr_text(
            ocr_combined_text=combined_ocr_text,
            per_image_ocr=per_image_ocr
        )
    except Exception as error:
        logger.error(f"Text interpretation failed: {error}")
        raise HTTPException(
            status_code=503,
            detail=f"AI text extraction failed: {str(error)}"
        )
    gemini_duration = time.time() - gemini_start

    # 4. Classification & Deterministic Compliance Engine
    compliance_start = time.time()
    source_info = {
        "type": "file",
        "file_count": len(uploaded_files),
        "files": file_metadata
    }
    compliance_result = check_compliance(extracted_data, source=source_info)
    compliance_duration = time.time() - compliance_start

    # 5. Build Explainable Report Locally
    report_start = time.time()
    report = build_inspection_report(
        extracted_data=extracted_data,
        compliance_result=compliance_result,
        inspection_type="package",
        source=source_info
    )
    report_duration = time.time() - report_start

    total_duration = time.time() - total_start_time

    # Construct timing & debug metadata
    timing_breakdown = {
        "upload_ms": int((ocr_start - total_start_time) * 1000),
        "ocr_ms": int(ocr_duration * 1000),
        "gemini_ms": int(gemini_duration * 1000),
        "compliance_ms": int(compliance_duration * 1000),
        "report_ms": int(report_duration * 1000),
        "total_ms": int(total_duration * 1000)
    }

    # Log step timing as specified in requirements
    logger.info(
        f"[INSPECT TIMING] "
        f"Images: {len(uploaded_files)} | "
        f"OCR: {ocr_duration:.2f}s | "
        f"Gemini (TEXT-ONLY): {gemini_duration:.2f}s | "
        f"Compliance: {compliance_duration:.3f}s | "
        f"Report: {report_duration:.3f}s | "
        f"Total: {total_duration:.2f}s"
    )

    per_image_previews = []
    for res in per_image_ocr:
        per_image_previews.append({
            "image_index": res.get("image_index"),
            "line_count": res.get("line_count"),
            "avg_confidence": res.get("confidence"),
            "text_preview": res.get("text", "")[:150] + ("..." if len(res.get("text", "")) > 150 else "")
        })

    report["ocr_debug"] = {
        "images_processed": len(uploaded_files),
        "ocr_status": "completed",
        "gemini_text_only": True,
        "combined_ocr_text": combined_ocr_text,
        "per_image_ocr": per_image_previews,
        "ocr_evidence": extracted_data.get("ocr_evidence", []),
        "timing": timing_breakdown
    }

    report["file"] = file_metadata[0] if len(file_metadata) == 1 else {
        "filename": f"{len(file_metadata)} package images",
        "content_type": "image/*",
        "files": file_metadata
    }

    report["project"] = "LegalCheck"
    report["problem_id"] = "SIH26034"

    return report


@app.post("/inspect-url")
async def inspect_url(payload: URLInspectRequest):
    total_start_time = time.time()
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

    report["ocr_debug"] = {
        "images_processed": 0,
        "ocr_status": "digital_web_extraction",
        "gemini_text_only": True,
        "timing": {
            "total_ms": int((time.time() - total_start_time) * 1000)
        }
    }

    report["project"] = "LegalCheck"
    report["problem_id"] = "SIH26034"

    return report