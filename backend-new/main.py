from fastapi import FastAPI, UploadFile, File

from controllers.user_controller import router as user_router

app = FastAPI()

# include user routes from controllers
app.include_router(user_router)

# File upload (unchanged)
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    return {"filename": file.filename, "content_type": file.content_type}

# Find (unchanged)
@app.get("/find/")
async def find(query: str):
    return {"message": f"Searching for '{query}'..."}


