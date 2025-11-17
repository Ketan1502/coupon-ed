from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import uuid
import bcrypt
from google.cloud import firestore
from google.oauth2 import service_account

router = APIRouter()

# Use explicit service account file, project id and database 'couponed'
credentials = service_account.Credentials.from_service_account_file(
    "keyfile.json"
)
db = firestore.Client(project="trial-project-478505", credentials=credentials)

# Pydantic models
class UserCreate(BaseModel):
    userName: str
    password: str

class UserOut(BaseModel):
    userId: str
    userName: str

@router.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate):
    users_ref = db.collection("users")  # 'users' is the kind/collection
    q = users_ref.where("userName", "==", user.userName).limit(1).get()
    if q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="userName already exists")

    user_id = uuid.uuid4().hex
    hashed = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    users_ref.document(user_id).set({
        "userId": user_id,
        "userName": user.userName,
        "password_hash": hashed
    })
    return UserOut(userId=user_id, userName=user.userName)

@router.post("/login/")
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