from fastapi import FastAPI, UploadFile, File

from controllers.user_controller import router as user_router
from controllers.upload_controller import router as upload_router
from controllers.search_controller import router as search_router
from controllers.coupons_controllers import router as coupons_router  # fixed import

app = FastAPI()

# include user routes from controllers
app.include_router(user_router)
app.include_router(upload_router)
app.include_router(search_router)
app.include_router(coupons_router)


