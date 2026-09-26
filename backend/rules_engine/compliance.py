from rules_engine.applicable_rules import determine_applicable_rules


def check_compliance(
    extracted_data: dict,
    inspection_type: str = "package",
    source: dict = None
) -> dict:
    applicability = determine_applicable_rules(extracted_data)

    violations = []
    passed = []
    visual_checks = []
    human_verification = []

    package_type = extracted_data.get("package_type", "unknown")

    for rule in applicability["applicable"]:
        field = rule["field"]
        value = extracted_data.get(field)

        if rule["check_type"] == "visual":
            visual_checks.append({
                "rule_id": rule["rule_id"],
                "rule_number": rule["rule_number"],
                "field": field,
                "status": "requires_visual_analysis",
                "requirement": rule["requirement"],
                "source": rule["source"]
            })
            continue

        # Special non-violation handling for unit_sale_price
        if field == "unit_sale_price":
            if value is not None and str(value).strip() != "":
                passed.append({
                    "rule_id": rule["rule_id"],
                    "rule_number": rule["rule_number"],
                    "field": field,
                    "detected_value": value,
                    "status": "detected",
                    "source": source
                })
            else:
                # Never mark unit_sale_price as a mandatory violation
                human_verification.append({
                    "rule_id": rule["rule_id"],
                    "field": field,
                    "description": "Unit sale price declaration review.",
                    "reason": "Unit sale price not detected. Verification recommended under Rule 6(11).",
                    "verification_status": "requires_verification"
                })
            continue

        if value is None or str(value).strip() == "":
            evidence_msg = (
                "The declaration was not found in the extracted public product-page content."
                if inspection_type == "digital"
                else "The declaration was not detected in the submitted package image."
            )
            violations.append({
                "rule_id": rule["rule_id"],
                "rule_number": rule["rule_number"],
                "field": field,
                "detected_value": None,
                "description": (
                    f"Required declaration '{field}' was not detected."
                ),
                "requirement": rule["requirement"],
                "source": rule["source"],
                "evidence": evidence_msg,
                "confidence": "requires_human_verification",
                "verification_status": "pending"
            })
        else:
            passed.append({
                "rule_id": rule["rule_id"],
                "rule_number": rule["rule_number"],
                "field": field,
                "detected_value": value,
                "status": "detected",
                "source": source
            })

    for item in applicability["requires_context"]:
        human_verification.append({
            "rule_id": item["rule_id"],
            "field": item["field"],
            "description": "Applicability could not be determined.",
            "reason": item["reason"],
            "verification_status": "pending"
        })

    # Overall Status Determination
    if violations:
        status = "potential_violation"
    elif human_verification or visual_checks:
        status = "requires_human_verification"
    else:
        status = "no_detected_violation"

    return {
        "status": status,
        "rules_summary": {
            "total_rules": applicability["total_rules"],
            "applicable": len(applicability["applicable"]),
            "not_applicable": len(applicability["not_applicable"]),
            "requires_context": len(applicability["requires_context"])
        },
        "applicable_rules": applicability["applicable"],
        "passed": passed,
        "violations": violations,
        "not_applicable": applicability["not_applicable"],
        "requires_context": applicability["requires_context"],
        "human_verification": human_verification,
        "visual_checks": visual_checks
    }
