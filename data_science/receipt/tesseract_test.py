import re

import cv2
import pytesseract
import numpy as np

def _order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def _four_point_transform(image, pts):
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = int(max(heightA, heightB))

    dst = np.array([[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxW, maxH))

def preprocess_receipt(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edge = cv2.Canny(blur, 50, 150)

    cnts, _ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    receipt = img
    for c in cnts[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            receipt = _four_point_transform(img, approx.reshape(4, 2))
            break

    rgray = cv2.cvtColor(receipt, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    rgray = clahe.apply(rgray)

    scale = 2.5
    rgray = cv2.resize(rgray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    rgray = cv2.bilateralFilter(rgray, 9, 75, 75)
    th = cv2.threshold(rgray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    return th

def ocr_receipt_tesseract(image_path: str) -> str:
    th = preprocess_receipt(image_path)
    config = "--oem 1 --psm 6"
    text = pytesseract.image_to_string(th, lang="jpn+eng", config=config)
    return text

if __name__ == "__main__":
    path = "PXL_20260212_113723927.jpg"
    text = ocr_receipt_tesseract(path)

    PRICE_RE = re.compile(r"(?:¥\s*)?(\d{1,3}(?:,\d{3})*|\d+)\s*$")

    def extract_items(ocr_text: str):
        items = []
        for line in ocr_text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = PRICE_RE.search(line)
            if not m:
                continue
            price = int(m.group(1).replace(",", ""))
            name = line[:m.start(1)].replace("¥", "").strip()
            if len(name) >= 2:
                items.append({"name": name, "price": price})
        return items
    
    print(text)

    text_items = extract_items(text)

    print(text_items)