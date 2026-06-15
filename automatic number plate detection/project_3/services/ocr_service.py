import re
import cv2
from datetime import datetime
from typing import Optional
from ultralytics import YOLO
import easyocr
import streamlit as st
from config import MODEL_PATH, OCR_ALLOW

PLATE_REGEX = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}$")

@st.cache_resource
def load_models(model_path: str = MODEL_PATH):
    model = YOLO(model_path)
    reader = easyocr.Reader(['en'], gpu=False)
    return model, reader

def clean_alnum(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

def remove_ind(s: str) -> str:
    return (s or "").replace("IND", "")

def bbox_center_y(bbox):
    ys = [pt[1] for pt in bbox]
    return sum(ys) / len(ys)

def normalize_ocr_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r",(\d)", r", \1", s)
    s = re.sub(r"(?<=\d)\.(?=\d)", ":", s)
    s = s.replace("_", " ")
    return s

def try_parse_overlay_datetime(text: str) -> Optional[datetime]:
    t = normalize_ocr_text(text).upper()
    m = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})', t)
    if m:
        s = m.group(1).replace("/", "-")
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    m = re.search(r'([A-Z]{3,9})\s+(\d{1,2}),?\s*(\d{4})\s+(\d{1,2}:\d{2}:\d{2})\s*(AM|PM)', t)
    if m:
        month, day, year, tim, ampm = m.group(1), m.group(2).zfill(2), m.group(3), m.group(4), m.group(5)
        text2 = f"{month} {day} {year} {tim} {ampm}"
        for fmt in ("%B %d %Y %I:%M:%S %p", "%b %d %Y %I:%M:%S %p"):
            try:
                return datetime.strptime(text2.title(), fmt)
            except Exception:
                pass
    return None

def extract_timestamp_from_frame(frame, reader):
    h, w = frame.shape[:2]
    rois = [
        frame[0:int(h * 0.18), int(w * 0.55):w],
        frame[int(h * 0.82):h, int(w * 0.55):w],
        frame[0:int(h * 0.18), 0:int(w * 0.45)],
    ]
    for roi in rois:
        if roi is None or roi.size == 0:
            continue
        roi2 = cv2.resize(roi, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)
        results = reader.readtext(roi2, detail=0)
        dtv = try_parse_overlay_datetime(" ".join(results))
        if dtv is not None:
            return dtv
    return None

def pad_crop(x1, y1, x2, y2, w, h, pad=8):
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w - 1, x2 + pad)
    y2 = min(h - 1, y2 + pad)
    return x1, y1, x2, y2

def preprocess_fast(plate_bgr):
    plate = cv2.resize(plate_bgr, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 7, 60, 60)
    adapt = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    return [("gray", gray), ("adapt", adapt)]

def merge_plate_from_easyocr(res_detail1):
    items = []
    for bbox, txt, conf in res_detail1:
        txtc = remove_ind(clean_alnum(txt))
        if not txtc or txtc == "IND":
            continue
        items.append((bbox_center_y(bbox), txtc, float(conf)))
    if not items:
        return "", 0.0
    items.sort(key=lambda x: x[0])
    merged = remove_ind(clean_alnum("".join([t for _, t, _ in items])))
    max_conf = max(c for _, _, c in items)
    if PLATE_REGEX.match(merged):
        return merged, max_conf
    m = re.search(r"[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}", merged)
    if m:
        return m.group(0), max_conf
    return merged, max_conf

def ocr_plate_fast(reader, plate_bgr):
    best_plate, best_conf = "", 0.0
    for vname, img in preprocess_fast(plate_bgr):
        res = reader.readtext(img, detail=1, allowlist=OCR_ALLOW, paragraph=False)
        if not res:
            continue
        plate, conf = merge_plate_from_easyocr(res)
        if not plate:
            continue
        valid = 1 if PLATE_REGEX.match(plate) else 0
        score = valid * 10.0 + conf
        best_valid = 1 if PLATE_REGEX.match(best_plate) else 0
        best_score = best_valid * 10.0 + best_conf
        if score > best_score:
            best_plate, best_conf = plate, conf
        if vname == "gray" and PLATE_REGEX.match(best_plate):
            break
    return best_plate, best_conf