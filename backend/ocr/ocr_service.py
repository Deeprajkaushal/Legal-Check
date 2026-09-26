import pytesseract
from PIL import Image


TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def extract_text(image_path: str) -> str:
    image = Image.open(image_path)

    text = pytesseract.image_to_string(
        image,
        lang="eng"
    )

    return text.strip()