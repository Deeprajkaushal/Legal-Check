import json
from pathlib import Path

RULES_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "rules"
    / "rules.json"
)


def load_rules() -> list[dict]:
    with open(RULES_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["rules"]


def determine_applicable_rules(extracted_data: dict) -> dict:
    rules = load_rules()

    category = extracted_data.get("product_category")
    is_imported = extracted_data.get("is_imported")
    has_shelf_life = extracted_data.get("has_shelf_life")
    package_type = extracted_data.get("package_type", "unknown")

    applicable = []
    not_applicable = []
    requires_context = []

    for rule in rules:
        rule_id = rule["rule_id"]
        field = rule["field"]
        applicability = rule.get("applicability", {})
        applies = True
        reason = ""

        # Special check for Unit Sale Price (Rule 6(11) - 2023 Amendment)
        if field == "unit_sale_price":
            if package_type in ("combination_package", "group_package", "multi_piece_package"):
                not_applicable.append({
                    "rule_id": rule_id,
                    "field": field,
                    "reason": (
                        "Rule 6(11) 2023 amendment: Unit sale price is not required "
                        f"for {package_type.replace('_', ' ')}s."
                    )
                })
                continue

        # Special check for Country of Origin (Rule 6(1)(aa))
        if field == "country_of_origin":
            if is_imported is True:
                applies = True
            elif is_imported is False:
                not_applicable.append({
                    "rule_id": rule_id,
                    "field": field,
                    "reason": "Country of origin requirement applies to imported products under Rule 6(1)(aa)."
                })
                continue
            else:
                requires_context.append({
                    "rule_id": rule_id,
                    "field": field,
                    "reason": "Import status is required to determine Country of Origin applicability under Rule 6(1)(aa)."
                })
                continue

        # Standard category checks
        categories = applicability.get("categories")
        if categories and "all" not in categories:
            if category is None:
                requires_context.append({
                    "rule_id": rule_id,
                    "field": field,
                    "reason": "Product category is required to determine applicability."
                })
                continue

            if category not in categories:
                applies = False
                reason = f"Rule is not configured for product category '{category}'."

        if "is_imported" in applicability and field != "country_of_origin":
            if is_imported is None:
                requires_context.append({
                    "rule_id": rule_id,
                    "field": field,
                    "reason": "Import status is required to determine applicability."
                })
                continue

            if is_imported != applicability["is_imported"]:
                applies = False
                reason = "Imported-product condition is not satisfied."

        if "has_shelf_life" in applicability:
            if has_shelf_life is None:
                requires_context.append({
                    "rule_id": rule_id,
                    "field": field,
                    "reason": "Shelf-life applicability could not be determined."
                })
                continue

            if has_shelf_life != applicability["has_shelf_life"]:
                applies = False
                reason = "Shelf-life condition is not satisfied."

        if applies:
            applicable.append({
                "rule_id": rule_id,
                "rule_number": rule["rule_number"],
                "field": field,
                "requirement": rule["requirement"],
                "check_type": rule["check_type"],
                "source": rule["source"]
            })
        else:
            not_applicable.append({
                "rule_id": rule_id,
                "field": field,
                "reason": reason
            })

    return {
        "applicable": applicable,
        "not_applicable": not_applicable,
        "requires_context": requires_context,
        "total_rules": len(rules)
    }
