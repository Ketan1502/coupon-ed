from google.cloud import storage
import os


BUCKET_NAME = os.environ.get("GCS_BUCKET")
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)


def upload_bytes_to_gcs(data: bytes, path: str) -> str:
blob = bucket.blob(path)
blob.upload_from_string(data)
blob.make_public()
return blob.public_url