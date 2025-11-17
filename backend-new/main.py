from fastapi import FastAPI, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import uuid
import bcrypt
from google.cloud import firestore
from google.cloud import datastore
from google.oauth2 import service_account

app = FastAPI()

# Use explicit service account file and project id
credentials = service_account.Credentials.from_service_account_file(
    "keyfile.json"
)
db = firestore.Client(project="trial-project-478505", credentials=credentials)

# Initialize Firestore client (requires GOOGLE_APPLICATION_CREDENTIALS env var to be set)
# db = firestore.Client()

# Pydantic models
class UserCreate(BaseModel):
    userName: str
    password: str

class UserOut(BaseModel):
    userId: str
    userName: str

# Create (register) user
@app.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate):
    # check if username already exists
    users_ref = db.collection("users")
    q = users_ref.where("userName", "==", user.userName).limit(1).get()
    if q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="userName already exists")

    user_id = uuid.uuid4().hex
    # hash password
    hashed = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    users_ref.document(user_id).set({
        "userId": user_id,
        "userName": user.userName,
        "password_hash": hashed
    })
    return UserOut(userId=user_id, userName=user.userName)

# Login (authenticate)
@app.post("/login/")
async def login(username: str, password: str):
    users_ref = db.collection("users")
    q = users_ref.where("userName", "==", username).limit(1).get()
    if not q:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user_doc = q[0].to_dict()
    stored_hash = user_doc.get("password_hash")
    if not stored_hash or not bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"message": f"Welcome {username}, you are logged in!", "userId": user_doc.get("userId")}

# File upload (unchanged)
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    return {"filename": file.filename, "content_type": file.content_type}

# Find (unchanged)
@app.get("/find/")
async def find(query: str):
    return {"message": f"Searching for '{query}'..."}



