from fastapi import FastAPI, UploadFile, File
from services.model_1 import generate_ad_template,post_data
import requests
import json

app = FastAPI()

@app.post("/generate_ad_template/")
async def generate_ad_template_endpoint(
    heading: str,
    desc: str,
    cta: str,
    contact: str,
    logo_path: UploadFile = File(...),
    product_path: UploadFile = File(...)
):
    logo_bytes = await logo_path.read()
    product_bytes = await product_path.read()
    layouts_info = generate_ad_template(heading, desc, cta, contact, logo_bytes, product_bytes)
    
    post_data(layouts_info)  # Send the generated layout info to the API
    
    return {
        "message": "Ad template generated and posted successfully",
        "layouts_info": layouts_info
    }

