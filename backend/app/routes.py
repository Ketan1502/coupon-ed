from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from .gcs_utils import upload_bytes_to_gcs
from .docai_utils import ocr_extract_text
from .vertex_utils import embed_text, upsert_vector, vector_search
from .firestore_utils import save_coupon, query_coupons_by_ids
import base64, uuid


router = APIRouter()


@router.post("/upload-coupon")
async def upload_coupon(image_b64: str, user_id: str = Form(...)):
# decode
image_bytes = base64.b64decode(image_b64)
coupon_id = str(uuid.uuid4())
gcs_uri = upload_bytes_to_gcs(image_bytes, f"{user_id}/{coupon_id}.png")


# OCR
raw_text = ocr_extract_text(gcs_uri)


# metadata extraction (can call Gemini here)
# For MVP, we'll keep raw_text and some simple tags


# embedding
embedding = embed_text(raw_text)


# upsert to vector index
upsert_vector(coupon_id, embedding, metadata={"user_id": user_id, "gcs_uri": gcs_uri})


# save metadata
doc = {
"coupon_id": coupon_id,
"user_id": user_id,
"image_gcs_uri": gcs_uri,
"raw_text": raw_text
}
save_coupon(doc)


return JSONResponse({"coupon_id": coupon_id})


@router.get("/search")
async def search(query: str, user_id: str):
q_embed = embed_text(query)
hits = vector_search(q_embed, namespace=user_id, top_k=5)
# hits -> extract ids
ids = [h["id"] for h in hits]
coupons = query_coupons_by_ids(ids)
return coupons