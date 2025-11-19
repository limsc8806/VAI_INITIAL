from PIL import Image
import pytesseract
import pdfplumber
import pathlib
import json

def extract_table_ocr(pdf_path, page_num=0, crop_bbox=None):
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_num]
        # 이미지로 변환
        im = page.to_image(resolution=300)
        if crop_bbox:
            im = im.crop(crop_bbox)
        pil_img = im.original
        # OCR 수행
        text = pytesseract.image_to_string(pil_img, lang='eng')
        return text

if __name__ == "__main__":
    pdf_path = pathlib.Path("data/raw/test_page.pdf")
    # 1페이지 전체 OCR
    ocr_text = extract_table_ocr(pdf_path, page_num=0)
    print("--- OCR 결과 (1페이지 전체) ---\n", ocr_text)
    # 필요시 crop_bbox=(x0, y0, x1, y1)로 표 영역만 지정 가능
