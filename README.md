# Coupon Backend + Streamlit UI (Coupon-Ed!)

This repository contains a small example backend (FastAPI) and a Streamlit frontend for uploading coupon images, creating embeddings (Vertex AI), and searching using a Vertex LLM.

Files of interest

- `main.py` - FastAPI app entry
- `controllers/` - controllers for users, uploads, and search
- `streamlit_app.py` - Streamlit frontend UI
- `requirements.txt` - Python dependencies
- `Dockerfile.backend` - Dockerfile for the FastAPI backend
- `Dockerfile.streamlit` - Dockerfile for the Streamlit frontend
- `CLOUD_RUN.md` - Cloud Run deployment instructions

Prerequisites

- Python 3.11
- gcloud SDK configured with your project
- A Google Cloud project with the following APIs enabled: Cloud Storage, Firestore, Vertex AI (aiplatform)
- Service account with permissions for Storage, Firestore, and Vertex AI. Use Workload Identity / Secret Manager in production.

Environment variables

- `GOOGLE_APPLICATION_CREDENTIALS` - path to service account keyfile (local dev only)
- `API_URL` - (optional) Streamlit will call this backend URL; defaults to http://127.0.0.1:8000
- `LLM_NAME` - Vertex model name (defaults to `text-bison@001`). For Gemini models, set to `gemini-pro-1.0` (if available in your project/region).

Local development

1. Create a venv and install deps

```powershell
python -m venv .venv; .\.venv\Scripts\Activate
pip install -r requirements.txt
```

2. Set credentials (local dev)

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\keyfile.json"
```

3. Run backend and Streamlit app in separate terminals

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
streamlit run streamlit_app.py
```

API endpoints (examples)

- Register

```bash
curl -X POST "http://127.0.0.1:8000/users/" -H "Content-Type: application/json" -d '{"userName":"alice","password":"pass"}'
```

- Login

```bash
curl -X POST "http://127.0.0.1:8000/login/?username=alice&password=pass"
```

- Upload image (example using curl)

```bash
curl -X POST "http://127.0.0.1:8000/upload/" -H "X-User-Id: <userId>" -F "file=@/path/to/coupon.png;type=image/png"
```

- Find/search

```bash
curl -X POST "http://127.0.0.1:8000/find/" -H "X-User-Id: <userId>" -H "Content-Type: application/json" -d '{"user_prompt":"I want shoes","system_prompt":"You are a coupon assistant","top_k":5}'
```

Deployment

- See `CLOUD_RUN.md` for Docker build and Cloud Run deployment instructions.

Security note

- Never commit `keyfile.json` or other secrets. Use `.gitignore` (already included) and use Secret Manager / Workload Identity for production.

Troubleshooting

- If Vertex model loading fails for Gemini names, list models with `gcloud ai models list --project=PROJECT --region=LOCATION` and confirm the model name and region. Some public models are region-limited or require access.
- If `pyarrow` or other wheel builds fail on Windows, consider using conda or a base image with build tools for Cloud Build.

Contact

- For additional help, paste runtime logs or error traces and I can help debug further.


Deployed Link

- Backend: https://coupon-backend-920211076670.europe-west1.run.app
- Frontend:  https://coupon-frontend-920211076670.europe-west1.run.app
  