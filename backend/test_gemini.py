from pathlib import Path
from ai.gemini_service import analyze_package_image

image_path = Path("test_package.jpg")

image_bytes = image_path.read_bytes()

result = analyze_package_image(
    image_bytes=image_bytes,
    mime_type="image/jpeg"
)

print("\n===== STRUCTURED GEMINI RESULT =====\n")

for field, value in result.items():
    print(f"{field}: {value}")