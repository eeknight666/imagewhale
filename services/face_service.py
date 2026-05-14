import os
import pickle
import numpy as np
from pathlib import Path
from PIL import Image
from io import BytesIO
from config import BASE_DIR

FACES_DB_DIR = os.path.join(BASE_DIR, "faces_db")
FACES_DB_FILE = os.path.join(FACES_DB_DIR, "faces_db.pkl")
MAX_SEARCH_IMAGE_LONG_EDGE = 1920

Path(FACES_DB_DIR).mkdir(parents=True, exist_ok=True)


def _load_faces_db() -> dict:
    if os.path.exists(FACES_DB_FILE):
        with open(FACES_DB_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def _save_faces_db(db: dict):
    with open(FACES_DB_FILE, "wb") as f:
        pickle.dump(db, f)


def register_face(name: str, image_content_list: list) -> dict:
    import face_recognition

    encodings = []
    for image_content in image_content_list:
        img = Image.open(BytesIO(image_content))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img_array = np.array(img)

        face_locations = face_recognition.face_locations(img_array)
        if len(face_locations) == 0:
            raise ValueError("有图片未检测到人脸，请上传清晰的正脸照")
        if len(face_locations) > 1:
            raise ValueError(f"有图片检测到{len(face_locations)}张人脸，请上传单人正脸照")

        face_encodings = face_recognition.face_encodings(img_array, face_locations)
        if len(face_encodings) == 0:
            raise ValueError("人脸特征提取失败")

        encodings.append(face_encodings[0])

    avg_encoding = np.mean(encodings, axis=0)

    faces_db = _load_faces_db()
    faces_db[name] = avg_encoding
    _save_faces_db(faces_db)

    return {"name": name, "count": len(encodings), "message": f"人脸注册成功（使用{len(encodings)}张照片）"}


def list_registered_faces() -> list:
    faces_db = _load_faces_db()
    return list(faces_db.keys())


def delete_registered_face(name: str) -> bool:
    faces_db = _load_faces_db()
    if name not in faces_db:
        return False
    del faces_db[name]
    _save_faces_db(faces_db)
    return True


def search_faces_in_image(image_content: bytes) -> dict:
    import face_recognition

    faces_db = _load_faces_db()
    if not faces_db:
        raise ValueError("暂无注册人脸，请先注册")

    known_names = list(faces_db.keys())
    known_encodings = list(faces_db.values())

    img = Image.open(BytesIO(image_content))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    width, height = img.size
    if max(width, height) > MAX_SEARCH_IMAGE_LONG_EDGE:
        ratio = MAX_SEARCH_IMAGE_LONG_EDGE / max(width, height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    img_array = np.array(img)

    face_locations = face_recognition.face_locations(img_array)
    if len(face_locations) == 0:
        raise ValueError("未检测到人脸")

    face_encodings = face_recognition.face_encodings(img_array, face_locations)

    matched_names = []
    for face_encoding in face_encodings:
        distances = face_recognition.face_distance(known_encodings, face_encoding)
        best_match_idx = np.argmin(distances)
        if distances[best_match_idx] < 0.6:
            matched_names.append(known_names[best_match_idx])

    return {
        "faces_detected": len(face_locations),
        "matched": len(matched_names) > 0,
        "matched_names": list(set(matched_names))
    }


def batch_search_faces(image_list: list) -> list:
    results = []
    for item in image_list:
        try:
            result = search_faces_in_image(item["content"])
            results.append({
                "filename": item["filename"],
                "matched": result["matched"],
                "matched_names": result["matched_names"],
                "faces_detected": result["faces_detected"]
            })
        except ValueError as e:
            results.append({
                "filename": item["filename"],
                "matched": False,
                "matched_names": [],
                "error": str(e)
            })
        except Exception:
            results.append({
                "filename": item["filename"],
                "matched": False,
                "matched_names": [],
                "error": "图片处理失败"
            })
    return results


def search_faces_in_project_images(image_paths: list, target_name: str) -> list:
    import face_recognition

    faces_db = _load_faces_db()
    if target_name not in faces_db:
        raise ValueError(f"未找到注册人脸: {target_name}")

    target_encoding = faces_db[target_name]
    results = []

    for image_id, image_filename, thumbnail_path in image_paths:
        file_path = os.path.join(BASE_DIR, "uploads", image_filename)
        if not os.path.exists(file_path):
            continue
        try:
            img = Image.open(file_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            width, height = img.size
            if max(width, height) > MAX_SEARCH_IMAGE_LONG_EDGE:
                ratio = MAX_SEARCH_IMAGE_LONG_EDGE / max(width, height)
                img = img.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)
            img_array = np.array(img)
            face_locations = face_recognition.face_locations(img_array)
            if not face_locations:
                continue
            face_encodings = face_recognition.face_encodings(img_array, face_locations)
            for face_encoding in face_encodings:
                distance = face_recognition.face_distance([target_encoding], face_encoding)[0]
                if distance < 0.6:
                    results.append({
                        "image_id": image_id,
                        "filename": image_filename,
                        "thumbnail_path": thumbnail_path,
                        "matched_name": target_name
                    })
                    break
        except Exception:
            continue

    return results
