from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, Header, HTTPException, status
import uuid
from google.cloud import storage
from google.oauth2 import service_account
import controllers.user_controller as user_controller  # reuse Firestore client and user collection
import os
import time
import json
import hashlib
import logging
import uuid as _uuid
import requests
import google.auth.transport.requests
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel


router = APIRouter()

# CONFIG - adjust as needed
KEYFILE_PATH = "keyfile.json"
PROJECT_ID = "trial-project-478505"
BUCKET_NAME = "couponed-eu-uploads"  # create this bucket or change to an existing one

LOCATION = "europe-west1"
PROJECT = "trial-project-478505"
MM_MODEL_NAME =  "multimodalembedding@001"
INDEX_PREFIX = "5995830420309016576"
NUM_SHARDS = 1
EMBEDDING_DIM = 512
KEYFILE = "keyfile.json"


# init storage client using same service account file used by user_controller
credentials = service_account.Credentials.from_service_account_file(
    "keyfile.json"
)
storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)

# dependency: validate X-User-Id header against Firestore users collection
async def get_current_user(x_user_id: str = Header(...)):
    doc_ref = user_controller.db.collection("users").document(x_user_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing user id")
    return doc.to_dict()

def send_to_vector_db(gcs_uri: str, user_id: str):
    """
    Download image from GCS -> compute embedding via Vertex AI MultiModalEmbeddingModel -> upsert to Vertex Index.

    Uses EMBEDDING_DIM env var (defaults to 512). Keeps metadata.user_id and shard routing.
    """
    

    LOCATION = "europe-west1"
    PROJECT = "trial-project-478505"
    MM_MODEL_NAME =  "multimodalembedding@001"
    INDEX_PREFIX = "5995830420309016576"
    NUM_SHARDS = 1
    EMBEDDING_DIM = 512
    KEYFILE = "keyfile.json"


    # init storage client using same service account file used by user_controller
    credentials = service_account.Credentials.from_service_account_file(
        "keyfile.json"
    )
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE


    # config (use env overrides if present)
    

    # choose target index (shard) based on user_id when multiple shards configured
    # if NUM_SHARDS > 1:
    #     h = hashlib.sha256(user_id.encode("utf-8")).digest()
    #     shard_idx = int.from_bytes(h[:4], "big") % NUM_SHARDS
    #     target_index = f"{INDEX_PREFIX}-{shard_idx}"
    # else:
    target_index = INDEX_PREFIX

    logging.info("[vector] selected index=%s for user=%s (shards=%s)", target_index, user_id, NUM_SHARDS)

    # 1) download image bytes from GCS (we still download to validate existence; Vertex SDK can load gs:// directly)
    try:
        bucket_name, blob_path = gcs_uri.replace("gs://", "").split('/', 1)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        # quick existence / size check
        _ = blob.size
    except Exception as e:
        logging.exception("Failed to access image in GCS: %s", e)
        return

    # 2) initialize vertex and compute embedding using MultiModalEmbeddingModel
    try:
        vertexai.init(project=PROJECT, location=LOCATION)
        print("Vertex AI initialized")
        model = MultiModalEmbeddingModel.from_pretrained(MM_MODEL_NAME)
        print("model obtained")
        # load image directly from GCS
        image = Image.load_from_file(gcs_uri)
        print("image loaded from GCS")
        embeddings = model.get_embeddings(image=image, contextual_text=None, dimension=EMBEDDING_DIM)
        print("embeddings obtained")
        vector = embeddings.image_embedding
        print(len(vector))
        if not vector:
            logging.error("No image_embedding returned from model")
            return
        if len(vector) != EMBEDDING_DIM:
            logging.error("Embedding dimension mismatch: got %s expected %s", len(vector), EMBEDDING_DIM)
            return
    except Exception as e:
        logging.exception("Vertex embedding failed: %s", e)
        return

    # 3) Upsert to Vertex Index (Matching Engine) and include metadata.user_id
    try:
        datapoint_id = f"{user_id}:{int(time.time() * 1000)}:{_uuid.uuid4().hex}"
        datapoint = {
            "datapointId": datapoint_id,
            "featureVector": vector,
        } 

        body = {"datapoints": [datapoint]}
        upsert_url = f"https://{LOCATION}aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/indexes/{target_index}:upsertDatapoints"
        print("upsert_url:", upsert_url)
        creds = google.oauth2.service_account.Credentials.from_service_account_file(KEYFILE, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        print("got creds")
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
        print("headers prepared")
        print("headers:", headers)
        r = requests.post(upsert_url, headers=headers, json=body, timeout=30)
        print(r.status_code)
        print("upsert request sent")
        r.raise_for_status()
        print("Upserted datapoint %s to index %s", datapoint_id, target_index)
    except Exception as e:
        logging.exception("Failed to upsert vector to Vertex index: %s", e)
        return

    print("[vector] ingestion completed for datapoint=%s", datapoint_id)
    return

@router.post("/upload/", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    filename = file.filename or f"{uuid.uuid4().hex}.bin"
    gcs_path = f"users/{current_user.get('userId')}/{uuid.uuid4().hex}_{filename}"

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(data, content_type=file.content_type)

    gcs_uri = f"gs://{BUCKET_NAME}/{gcs_path}"

    if background_tasks is not None:
        background_tasks.add_task(send_to_vector_db, gcs_uri, current_user.get("userId"))
    else:
        send_to_vector_db(gcs_uri, current_user.get("userId"))

    return {"gcs_uri": gcs_uri, "filename": filename}