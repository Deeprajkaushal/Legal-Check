from rules_engine.compliance import check_compliance


# Simulated AI extraction.
# Gemini is NOT needed for this test.
sample_package = {
    "product_name": "Parle-G Gluco Biscuits",
    "manufacturer": "Parle Products Pvt Ltd",
    "manufactured_for": "Parle Products Pvt Ltd",
    "net_quantity": "70g",
    "mrp": None,
    "manufacturing_date": None,
    "best_before": None,
    "country_of_origin": None,
    "consumer_care": "Consumer Care Cell",
    "is_imported": False
}


result = check_compliance(sample_package)


print("\n==============================")
print("LEGALCHECK COMPLIANCE RESULT")
print("==============================\n")

print("Status:", result["status"])

print(
    "Rules checked:",
    result["rules_summary"]["total_rules"]
)

print("\nPASSED:")

for item in result["passed"]:
    print(
        f"  [PASS] {item['field']}: "
        f"{item['detected_value']}"
    )

print("\nPOTENTIAL VIOLATIONS:")

for item in result["violations"]:
    print(
        f"  [FAIL] {item['field']}: "
        f"{item['description']}"
    )

print("\nNOT APPLICABLE:")

for item in result["not_applicable"]:
    print(
        f"  - {item['field']}: "
        f"{item['reason']}"
    )