from fastapi import FastAPI
from app.routes import router


app = FastAPI(title="coupon-ed-backend")
app.include_router(router, prefix="/api")

#test


@app.get("/")
def root():
return {"status": "ok"}