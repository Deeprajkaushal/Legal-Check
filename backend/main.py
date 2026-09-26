from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.gemini_service import analyze_package_image, analyze_web_content
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
    version="0.2.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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
        "version": "0.2.0"
    }


@app.post("/inspect")
async def inspect_package(
    image: UploadFile = File(...)
):
    if not image.content_type:
        raise HTTPException(
            status_code=400,
            detail="Could not determine image type."
        )

    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload an image file."
        )

    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty."
        )

    # ---------------------------------------------
    # AI extraction + classification
    # ---------------------------------------------

    try:
        extracted_data = analyze_package_image(
            image_bytes=image_bytes,
            mime_type=image.content_type
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"AI extraction failed: {str(error)}"
        )

    # ---------------------------------------------
    # Deterministic compliance analysis
    # ---------------------------------------------

    compliance_result = check_compliance(
        extracted_data
    )

    # ---------------------------------------------
    # Explainable inspection report
    # ---------------------------------------------

    report = build_inspection_report(
        extracted_data=extracted_data,
        compliance_result=compliance_result,
        inspection_type="package",
        source={"type": "file", "filename": image.filename}
    )

    report["file"] = {
        "filename": image.filename,
        "content_type": image.content_type
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

        # Handle JS-only/unextractable or timeout pages gracefully with requires_human_verification
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