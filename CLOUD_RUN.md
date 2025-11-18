# Deploy to Cloud Run - Backend + Frontend

This file documents a minimal flow to build and deploy the FastAPI backend and Streamlit frontend to Cloud Run.

Prerequisites

- gcloud SDK installed and authenticated
- Docker installed (if you plan to build locally)
- Set your project and region:

```powershell
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region europe-west1
```

Build & push (using Docker locally)

```powershell
# replace YOUR_PROJECT_ID
$PROJECT_ID=YOUR_PROJECT_ID
# Backend image
docker build -f Dockerfile.backend -t gcr.io/$PROJECT_ID/coupon-backend:latest .
# Frontend image
docker build -f Dockerfile.streamlit -t gcr.io/$PROJECT_ID/coupon-frontend:latest .

# Authenticate Docker to push
gcloud auth configure-docker

docker push gcr.io/$PROJECT_ID/coupon-backend:latest
docker push gcr.io/$PROJECT_ID/coupon-frontend:latest
```

Deploy to Cloud Run

```powershell
# Backend
gcloud run deploy coupon-backend \
  --image gcr.io/$PROJECT_ID/coupon-backend:latest \
  --region europe-west1 --platform managed \
  --allow-unauthenticated --port 8080 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID

# Frontend (Streamlit)
# Note: Cloud Run services are public by default if allow-unauthenticated is set. If you want auth, remove that flag and configure IAM.

gcloud run deploy coupon-frontend \
  --image gcr.io/$PROJECT_ID/coupon-frontend:latest \
  --region europe-west1 --platform managed \
  --allow-unauthenticated --port 8080 \
  --set-env-vars API_URL="https://$(gcloud run services describe coupon-backend --region=europe-west1 --format='value(status.url)')"
```

Secrets and credentials

- Do NOT bake service account keyfiles into the image. Use Workload Identity or Cloud Run service account and Secret Manager for keys.
- To use a keyfile from Secret Manager, create the secret and mount or fetch at runtime in your startup script.

Notes

- Ensure the service account used by Cloud Run has permissions for Firestore, Storage, and Vertex AI.
- If you experience build errors for packages like `pyarrow` on Cloud Build, consider using a base image with the required build tools or building with --platform and explicit build steps.

Troubleshooting

- If your Streamlit app needs to call the backend, set `API_URL` env var on the frontend Cloud Run service to point to the backend's URL (see example above).
- For Vertex AI model access, ensure the Cloud Run service account has the `roles/aiplatform.user` (or appropriate) role and the same region is used for Vertex calls.
