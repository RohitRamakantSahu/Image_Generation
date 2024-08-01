from fastapi import FastAPI, UploadFile, File
from services.model_1 import generate_ad_template
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

# Function to post data
def post_data(data_array):
    url = 'http://dev.api.sparkiq.ai/generate-images'
    for data in data_array:
        try:
            print(f"Sending data: {json.dumps(data, indent=4)}")
            response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
            response.raise_for_status()  # Check for HTTP errors
            print('POST response:', json.dumps(response.json(), indent=4))
        except requests.exceptions.RequestException as e:
            print('Error:', e)
    
    # After posting all data, make a GET request to fetch all data
    try:
        get_response = requests.get(url)
        get_response.raise_for_status()  # Check for HTTP errors
        print('GET response:', json.dumps(get_response.json(), indent=4))
    except requests.exceptions.RequestException as e:
        print('Error:', e)
