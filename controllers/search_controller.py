# from fastapi import APIRouter, Depends, HTTPException, status
# from pydantic import BaseModel
# from google.oauth2 import service_account
# import os
# import logging
# import time
# from typing import Optional

# import controllers.upload_controller as upload_controller
# from controllers.upload_controller import storage_client, BUCKET_NAME
# import uuid

# router = APIRouter()


# class FindRequest(BaseModel):
#     user_prompt: str
#     system_prompt: Optional[str] = ""
#     top_k: int = 5


# @router.post("/find/")
# async def find(req: FindRequest, current_user=Depends(upload_controller.get_current_user)):
#     """
#     Search for coupons for the authenticated user.

#     Flow:
#     - compute text embedding for user_prompt via Vertex MultiModalEmbeddingModel
#     - list user's uploaded coupon objects from GCS
#     - compose a prompt (system + user + coupon list + short embedding summary)
#     - call Vertex LLM (if available) to evaluate and return a response
#     """
#     # read configuration
#     LLM_NAME = "gemini-2.5-flash"
#     LOCATION = "europe-west1"
#     PROJECT = "trial-project-478505"
#     MM_MODEL_NAME =  "multimodalembedding@001"
#     INDEX_PREFIX = "5995830420309016576"
#     NUM_SHARDS = 1
#     EMBEDDING_DIM = 512
#     KEYFILE = "keyfile.json"

#     user_id = current_user.get("userId")

#     credentials = service_account.Credentials.from_service_account_file(
#         "keyfile.json"
#     )
#     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE

#     # 1) compute text embedding using Vertex multimodal model (text embedding)
#     vector = None
#     try:
#         try:
#             import vertexai
#             from vertexai.vision_models import MultiModalEmbeddingModel
#         except Exception:
#             vertexai = None
#         if vertexai is None:
#             raise RuntimeError("vertexai SDK not available")

#         vertexai.init(project=PROJECT, location=LOCATION)
#         MODEL = GeneriativeModel("gemini")
#         mm = MultiModalEmbeddingModel.from_pretrained(MM_MODEL_NAME)
#         embeddings = mm.get_embeddings(image=None, contextual_text=req.user_prompt, dimension=EMBEDDING_DIM)
#         vector = embeddings.text_embedding
#         if not vector or len(vector) != EMBEDDING_DIM:
#             logging.error("embedding missing or wrong dimension: got %s expected %s", len(vector) if vector else None, EMBEDDING_DIM)
#             vector = None
#     except Exception as e:
#         logging.exception("Failed to compute text embedding: %s", e)

#     # 2) list user's uploaded coupons from GCS (prefix: users/{userId}/)
#     coupons = []
#     try:
#         prefix = f"users/{user_id}/"
#         bucket = storage_client.bucket(BUCKET_NAME)
#         blobs = list(bucket.list_blobs(prefix=prefix))
#         for b in blobs:

#             coupons.append({"name": os.path.basename(b.name), "gcs_uri": f"gs://{BUCKET_NAME}/{b.name}", "size": b.size})
#     except Exception as e:
#         logging.exception("Failed to list user uploads: %s", e)

#     # 3) compose prompt for LLM
#     system = req.system_prompt or "You are an assistant that helps a user find relevant coupons for their intent."
#     user_text = req.user_prompt

#     coupon_lines = "\n".join([f"- {c['name']} ({c['gcs_uri']})" for c in coupons]) or "(no coupons found)"

#     # create image embeddings for this user's images (do not persist them)
#     try:
#         image_embeddings = create_embeddings_for_user(user_id, save_to_firestore=False, max_images=req.top_k)
#     except Exception as e:
#         logging.exception("Failed to create embeddings for user images: %s", e)
#         image_embeddings = []

#     embedding_summary = f"embedding_length={len(vector) if vector else 0} images_embedded={len(image_embeddings)}"

#     def format_embeddings_for_prompt(emb_list, max_components: int = 12):
#         """
#         Produce a compact text preview of embeddings suitable for inclusion in an LLM prompt.
#         For each image include: name, gcs_uri, and a short numeric preview (first N components rounded).
#         """
#         lines = []
#         for e in emb_list:
#             emb = e.get('embedding') or []
#             preview = ','.join([f"{x:.4f}" for x in emb[:max_components]])
#             if len(emb) > max_components:
#                 preview = preview + ",..."
#             lines.append(f"- {e.get('name')} | {e.get('gcs_uri')} | emb_preview=[{preview}] (dim={e.get('dimension')})")
#         return "\n".join(lines) or "(no embeddings)"

#     embeddings_block = format_embeddings_for_prompt(image_embeddings, max_components=12)

#     full_prompt = f"System:\n{system}\n\nUser:\n{user_text}\n\nUser Coupons:\n{coupon_lines}\n\nEmbedding summary:\n{embedding_summary}\n\nTask: Based on the user intent and available coupons, tell the user whether there are relevant coupons and summarize them. Be concise."
#     # Append the embeddings block so the LLM can reason over the image embeddings inline.
#     full_prompt = full_prompt + "\n\nImage Embeddings:\n" + embeddings_block

#     # 4) call Vertex LLM (if available) to generate answer
#     answer = None
#     try:
#         try:
#             from vertexai.preview.language_models import TextGenerationModel
#         except Exception:
#             TextGenerationModel = None
#         if TextGenerationModel is None:
#             raise RuntimeError("Vertex LLM SDK not available")

#         llm = TextGenerationModel.from_pretrained(LLM_NAME)
#         # The Vertex SDK has changed across releases; try a few common method names
#         response = None
#         if hasattr(llm, "generate"):
#             response = llm.generate(prompt=full_prompt, max_output_tokens=512)
#         elif hasattr(llm, "predict"):
#             # some SDK versions use predict(text)
#             try:
#                 response = llm.predict(full_prompt, max_output_tokens=512)
#             except TypeError:
#                 response = llm.predict(full_prompt)
#         elif hasattr(llm, "create"):
#             # some preview APIs use create(input=...)
#             try:
#                 response = llm.create(input=full_prompt, max_output_tokens=512)
#             except TypeError:
#                 response = llm.create(input=full_prompt)
#         else:
#             raise RuntimeError("TextGenerationModel has no generate/predict/create method")

#         # Normalize response to extract text
#         if response is None:
#             raise RuntimeError("No response from LLM")

#         # Common shapes: response.generations[0].text, response.text, list of generations, or simple string
#         if hasattr(response, "generations") and response.generations:
#             # response.generations may be a list of lists or list of Generation objects
#             first = response.generations[0]
#             # if nested list
#             if isinstance(first, (list, tuple)) and first:
#                 gen = first[0]
#                 answer = getattr(gen, "text", str(gen))
#             else:
#                 answer = getattr(first, "text", str(first))
#         elif isinstance(response, (list, tuple)) and response:
#             # list of Generation-like objects
#             gen = response[0]
#             answer = getattr(gen, "text", str(gen))
#         elif hasattr(response, "text"):
#             answer = response.text
#         elif isinstance(response, str):
#             answer = response
#         else:
#             answer = str(response)
#     except Exception as e:
#         logging.exception("LLM call failed, returning fallback: %s", e)
#         # fallback: simple heuristic reply
#         if coupons:
#             answer = f"I found {len(coupons)} coupon(s). Example: {coupons[0]['name']} ({coupons[0]['gcs_uri']})."
#         else:
#             answer = "I couldn't find any coupons for your account."

#     return {"answer": answer, "coupon_count": len(coupons), "embedding_available": vector is not None}

#     # New function to create embeddings for user images
# def create_embeddings_for_user(user_id: str, save_to_firestore: bool = True, max_images: Optional[int] = None):
#     """
#     List all images for a user in GCS (prefix users/{user_id}/), compute image embeddings using
#     Vertex MultiModalEmbeddingModel, and return a list of embedding records:

#     [
#       {
#         "datapoint_id": str,
#         "gcs_uri": str,
#         "name": str,
#         "embedding": [float],
#         "dimension": int,
#         "created_at": int (epoch secs)
#       },
#       ...
#     ]

#     If save_to_firestore is True the embedding documents will be stored in Firestore under
#     collection `image_embeddings` (document id = datapoint_id).
#     """
#     results = []
#     try:
#         MM_MODEL_NAME = upload_controller.MM_MODEL_NAME
#         LOCATION = upload_controller.LOCATION
#         PROJECT = upload_controller.PROJECT
#         EMBEDDING_DIM = upload_controller.EMBEDDING_DIM
#         KEYFILE = upload_controller.KEYFILE
#     except Exception:
#         # fallback defaults
#         MM_MODEL_NAME = "multimodalembedding@001"
#         LOCATION = "europe-west1"
#         PROJECT = "trial-project-478505"
#         EMBEDDING_DIM = 512
#         KEYFILE = "keyfile.json"

#     # ensure GOOGLE_APPLICATION_CREDENTIALS is set for Vertex SDK
#     try:
#         os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE
#     except Exception:
#         pass

#     try:
#         import vertexai
#         from vertexai.vision_models import Image, MultiModalEmbeddingModel
#     except Exception as e:
#         logging.exception("Vertex SDK not available: %s", e)
#         return results

#     try:
#         vertexai.init(project=PROJECT, location=LOCATION)
#         model = MultiModalEmbeddingModel.from_pretrained(MM_MODEL_NAME)
#     except Exception as e:
#         logging.exception("Failed to init Vertex or load model: %s", e)
#         return results

#     # list blobs for user
#     try:
#         prefix = f"users/{user_id}/"
#         bucket = storage_client.bucket(BUCKET_NAME)
#         blobs = list(bucket.list_blobs(prefix=prefix))
#     except Exception as e:
#         logging.exception("Failed to list user blobs: %s", e)
#         return results

#     count = 0
#     for b in blobs:
#         if max_images and count >= max_images:
#             break
#         try:
#             gcs_uri = f"gs://{BUCKET_NAME}/{b.name}"
#             image = Image.load_from_file(gcs_uri)
#             embeddings = model.get_embeddings(image=image, contextual_text=None, dimension=EMBEDDING_DIM)
#             vector = getattr(embeddings, 'image_embedding', None)
#             if not vector:
#                 logging.warning("No image_embedding for %s", gcs_uri)
#                 continue
#             if len(vector) != EMBEDDING_DIM:
#                 logging.warning("Embedding dim mismatch for %s: got %s expected %s", gcs_uri, len(vector), EMBEDDING_DIM)
#                 # still include but mark dimension

#             datapoint_id = f"{user_id}:{int(time.time() * 1000)}:{uuid.uuid4().hex}"
#             doc = {
#                 "datapoint_id": datapoint_id,
#                 "user_id": user_id,
#                 "gcs_uri": gcs_uri,
#                 "name": os.path.basename(b.name),
#                 "embedding": vector,
#                 "dimension": len(vector),
#                 "created_at": int(time.time())
#             }

#             if save_to_firestore:
#                 try:
#                     # reuse Firestore client from upload_controller -> user_controller.db
#                     upload_controller.user_controller.db.collection("image_embeddings").document(datapoint_id).set(doc)
#                 except Exception as e:
#                     logging.exception("Failed to save embedding to Firestore for %s: %s", gcs_uri, e)

#             results.append(doc)
#             count += 1
#         except Exception as e:
#             logging.exception("Failed to compute embedding for blob %s: %s", b.name, e)
#             continue

#     return results

import logging
import math
from fastapi import APIRouter, HTTPException, status, Body, Depends
from google.cloud import storage
from google.oauth2 import service_account
import os
import vertexai
from vertexai.vision_models import Image, MultiModalEmbeddingModel
from vertexai.generative_models import GenerativeModel, Part
from pydantic import BaseModel
import controllers.upload_controller as upload_controller
from controllers.upload_controller import storage_client, BUCKET_NAME


router = APIRouter()

# Configuration from old-search.py
BUCKET_NAME = "couponed-eu-uploads" # Still get bucket name from env
PROJECT = "trial-project-478505"
LOCATION = "europe-west1"
MM_MODEL_NAME = "multimodalembedding@001"
LLM_NAME = "gemini-1.5-flash-preview-0514" # Using the flash model as previously agreed
KEYFILE = "keyfile.json"

# Set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI
credentials = service_account.Credentials.from_service_account_file(KEYFILE)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE

storage_client = storage.Client()

# Initialize Vertex AI
vertexai.init(project=PROJECT, location=LOCATION)

class SearchRequest(BaseModel):
    user_prompt: str
    top_n: int = 5

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if not magnitude1 or not magnitude2:
        return 0
    return dot_product / (magnitude1 * magnitude2)

@router.post("/find/")
async def search_with_images(request: SearchRequest, current_user=Depends(upload_controller.get_current_user)):
    """
    Search for coupons for the authenticated user using multimodal search.
    """
    user_id = current_user.get("userId")

    # Configuration from old-search.py
    BUCKET_NAME = "couponed-eu-uploads" # Still get bucket name from env
    PROJECT = "trial-project-478505"
    LOCATION = "europe-west1"
    MM_MODEL_NAME = "multimodalembedding@001"
    # LLM_NAME = "gemini-1.5-flash-preview-0514" # Using the flash model as previously agreed
    LLM_NAME = "gemini-2.5-flash"
    KEYFILE = "keyfile.json"

    # Set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI
    credentials = service_account.Credentials.from_service_account_file(KEYFILE)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEYFILE

    storage_client = storage.Client()

    # Initialize Vertex AI
    vertexai.init(project=PROJECT, location=LOCATION)

    if not BUCKET_NAME: # Only check for BUCKET_NAME as PROJECT is hardcoded
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is not configured. Missing GCS_BUCKET_NAME."
        )

    try:
        # 1. Get embeddings
        embedding_model = MultiModalEmbeddingModel.from_pretrained(MM_MODEL_NAME)
        
        # Get text embedding for the user's prompt
        prompt_embedding = embedding_model.get_embeddings(contextual_text=request.user_prompt).text_embedding
        #         embeddings = mm.get_embeddings(image=None, contextual_text=req.user_prompt, dimension=EMBEDDING_DIM)

        # Get image embeddings for all coupons
        prefix = f"users/{user_id}/"
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = list(bucket.list_blobs(prefix=prefix))


        #     # 2) list user's uploaded coupons from GCS (prefix: users/{userId}/)
#     coupons = []
#     try:
#         prefix = f"users/{user_id}/"
#         bucket = storage_client.bucket(BUCKET_NAME)
#         blobs = list(bucket.list_blobs(prefix=prefix))
#         for b in blobs:

#             coupons.append({"name": os.path.basename(b.name), "gcs_uri": f"gs://{BUCKET_NAME}/{b.name}", "size": b.size})
#     except Exception as e:
#         logging.exception("Failed to list user uploads: %s", e)

        if not blobs:
            raise HTTPException(status_code=404, detail="No coupons found for user.")

        coupon_data = []
        for blob in blobs:
            if blob.name.endswith('/'):
                continue
            
            image_bytes = blob.download_as_bytes()
            image_embedding = embedding_model.get_embeddings(image=Image(image_bytes)).image_embedding
            coupon_data.append({
                "image_bytes": image_bytes,
                "embedding": image_embedding,
                "blob_name": blob.name
            })

        # 2. Calculate similarity and find top N results
        for coupon in coupon_data:
            coupon["similarity"] = cosine_similarity(prompt_embedding, coupon["embedding"])

        coupon_data.sort(key=lambda x: x["similarity"], reverse=True)
        
        top_n = request.top_n
        top_coupons = coupon_data[:top_n]

        # 3. Generate a response with Gemini 1.5 Flash
        model = GenerativeModel(LLM_NAME)

        system_prompt = (
            "You are an expert assistant. The user has provided you with a question and a set of their most relevant coupon images. "
            "Your task is to answer the user's question based *only* on the information visible in these images. "
            "Be precise and refer to the coupons when possible."
            "If relevant coupons are not found in the images, respond with 'No relevant coupons found, don't mention about coupons not asked ofr by the user."
        )

        # Create the prompt parts
        prompt_parts = [system_prompt, f"User's question: {request.user_prompt}\n\nHere are the most relevant coupons:\n"]
        for coupon in top_coupons:
            # TODO: Infer mime_type from blob name or content
            prompt_parts.append(Part.from_data(coupon["image_bytes"], mime_type="image/jpeg"))

        response = model.generate_content(prompt_parts)

        return {"answer": response.text}

    except Exception as e:
        logging.exception("Failed during search: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during search: {e}"
        )
