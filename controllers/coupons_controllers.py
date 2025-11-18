# controllers/coupons_controller.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
import os
import base64
import logging
from google.cloud import storage
from google.oauth2 import service_account

import controllers.upload_controller as upload_controller
from controllers.upload_controller import BUCKET_NAME, storage_client, get_current_user

router = APIRouter()

# Ensure credentials (re-use existing keyfile path if needed)
KEYFILE = "keyfile.json"
if os.path.exists(KEYFILE):
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE
    except Exception:
        pass

@router.get("/coupons/", status_code=200)
async def list_user_coupons(
    current_user = Depends(get_current_user),
    limit: Optional[int] = Query(None, gt=0, description="Max number of coupons to return"),
    include_signed_url: bool = Query(True, description="Include time-limited signed URL for display"),
    include_data: bool = Query(False, description="Include Base64 image bytes (use sparingly)"),
    url_expiry_seconds: int = Query(900, gt=60, lt=86400, description="Signed URL expiry in seconds")
):
    """
    List coupon images for the logged-in user.
    """
    user_id = current_user.get("userId")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user id")

    if not BUCKET_NAME:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bucket not configured")

    prefix = f"users/{user_id}/"
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs_iter = bucket.list_blobs(prefix=prefix)
        blobs = []
        for b in blobs_iter:
            # skip directory placeholders
            if b.name.endswith("/"):
                continue
            blobs.append(b)
            if limit and len(blobs) >= limit:
                break
    except Exception as e:
        logging.exception("Failed to list blobs for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to list coupons")

    if not blobs:
        return {"userId": user_id, "count": 0, "coupons": []}

    results: List[dict] = []
    for b in blobs:
        try:
            gcs_uri = f"gs://{BUCKET_NAME}/{b.name}"
            item = {
                "name": os.path.basename(b.name),
                "gcs_uri": gcs_uri,
                "size": b.size,
                "content_type": b.content_type,
                "updated": b.updated.isoformat() if b.updated else None
            }

            if include_signed_url:
                try:
                    url = b.generate_signed_url(version="v4", expiration=url_expiry_seconds, method="GET")
                    item["signed_url"] = url
                except Exception as e:
                    logging.warning("Signed URL failed for %s: %s", b.name, e)

            if include_data:
                try:
                    # Caution: increases payload size
                    data = b.download_as_bytes()
                    item["image_base64"] = base64.b64encode(data).decode("utf-8")
                except Exception as e:
                    logging.warning("Failed to inline bytes for %s: %s", b.name, e)

            results.append(item)
        except Exception as e:
            logging.warning("Skipping blob %s due to error: %s", b.name, e)
            continue

    return {
        "userId": user_id,
        "count": len(results),
        "coupons": results
    }