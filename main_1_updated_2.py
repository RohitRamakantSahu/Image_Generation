from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from services.model_1 import generate_ad_template, post_data
import json

app = FastAPI()

class AdTemplateRequest(BaseModel):
    heading: str
    desc: str
    cta: str
    contact: str

@app.post("/generate_ad_template/")
async def generate_ad_template_endpoint(
    request: str = Form(...),
    logo_path: UploadFile = File(...),
    product_path: UploadFile = File(...)
):
    try:
        # Parse the JSON string into a dictionary
        request_dict = json.loads(request)
        ad_request = AdTemplateRequest(**request_dict)
        
        logo_bytes = await logo_path.read()
        product_bytes = await product_path.read()
        
        # Generate the ad template
        layouts_info = generate_ad_template(
            ad_request.heading,
            ad_request.desc,
            ad_request.cta,
            ad_request.contact,
            logo_bytes,
            product_bytes
        )
        
        # Post the data
        post_data(layouts_info)
        
        return {
            "message": "Ad template generated and posted successfully",
            "layouts_info": layouts_info
        }
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in request field"}
    except Exception as e:
        return {"error": str(e)}
