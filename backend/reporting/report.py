from datetime import datetime, timezone
import uuid


def build_inspection_report(
    extracted_data: dict,
    compliance_result: dict,
    inspection_type: str = "package",
    source: dict = None,
) -> dict:
    """Build the API response used by the LegalCheck frontend."""
    now = datetime.now(timezone.utc)

    inspection_id = (
        "LC-"
        + now.strftime("%Y%m%d")
        + "-"
        + uuid.uuid4().hex[:8].upper()
    )

    verification_msg = (
        "This inspection is based on information publicly available on the supplied product page. Physical package verification may be required."
        if inspection_type == "digital"
        else (
            "This is an AI-assisted screening result. "
            "Findings should be verified by a qualified person before legal or enforcement action."
        )
    )

    return {
        "inspection_id": inspection_id,
        "inspection_type": inspection_type,
        "source": source or {"type": "file"},
        "generated_at": now.isoformat(),
        "product": {
            "name": extracted_data.get("product_name"),
            "category": extracted_data.get("product_category"),
            "category_confidence": extracted_data.get("category_confidence"),
            "category_evidence": extracted_data.get("category_evidence"),
            "package_type": extracted_data.get("package_type", "unknown"),
        },
        "context": {
            "is_imported": extracted_data.get("is_imported"),
            "has_shelf_life": extracted_data.get("has_shelf_life"),
            "package_type": extracted_data.get("package_type", "unknown"),
        },
        "shelf_life": extracted_data.get("shelf_life"),
        "declarations": extracted_data,
        "compliance": compliance_result,
        "verification": {
            "status": "pending_human_verification",
            "message": verification_msg,
        },
        "legal_references": {
            "shelf_life": "Rule 6(1)(da): Best Before / Use By for applicable commodities",
            "country_of_origin": "Rule 6(1)(aa): Country of origin/manufacture/assembly for imported products",
            "unit_sale_price": "Rule 6(11): Unit Sale Price and its applicability",
            "unit_sale_price_exemption": "Rule 6(11) 2023 Amendment: Exemption for combination/group/multi-piece packages",
        },
    }
