import os
from datetime import datetime
from werkzeug.utils import secure_filename
from .db_utils import connect_to_mongo

# Directory to save uploaded patch files
PATCH_UPLOAD_DIR = "uploaded_patches"
os.makedirs(PATCH_UPLOAD_DIR, exist_ok=True)

def save_patch_file(file):
    filename = f"{datetime.utcnow().isoformat()}_{secure_filename(file.filename)}"
    filepath = os.path.join(PATCH_UPLOAD_DIR, filename)
    file.save(filepath)
    return filename, filepath

def log_patch_to_db(service, description, filename, filepath):
    client, db = connect_to_mongo()
    if db is None:
        raise Exception("Database connection failed")

    patch = {
        "service": service,
        "description": description,
        "timestamp": datetime.utcnow(),
        "filename": filename,
        "filepath": filepath,
        "status": "pending"
    }

    result = db.patches.insert_one(patch)
    return result.inserted_id

def get_patches_by_service(service_name):
    client, db = connect_to_mongo()
    if db is None:
        raise Exception("Database connection failed")

    patches = db.patches.find({"service": service_name}).sort("timestamp", -1)
    return [
        {
            "id": str(patch["_id"]),
            "service": patch["service"],
            "description": patch["description"],
            "filename": patch["filename"],
            "filepath": patch["filepath"],
            "timestamp": patch.get("timestamp"),
            "status": patch.get("status"),
        }
        for patch in patches
    ]
