from fastapi import FastAPI, Request,Response
import requests
from dotenv import load_dotenv
from OllypollyAi import perform_vector_search, get_query_embedding,perform_vector_search_for_specfic_Chatbot
from fastapi.responses import JSONResponse
import uvicorn

load_dotenv()
app = FastAPI()

@app.get("/")
def home():
    return "Hello, This is Home."

@app.get("/image_link/")
def get_item(phone_modal: str,image_url: str):
    """Handles the user's image upload and returns similar products."""
    try:
        resp = requests.get(image_url, stream=True, timeout=30)
        # Read the file bytes directly from the stream
        image_bytes = resp.content
        # 1. Encoding (Gets the Query Vector)
        query_vector = get_query_embedding(image_bytes)
        # 2. Vector Search in DB
        results, status_code = perform_vector_search(phone_modal,query_vector)

        if status_code != 200:
            return JSONResponse(results, status_code)
        
        advance_response_data = {
            "Name:": results["name"],
            "Link:": results["Link"]
        }
        return advance_response_data
    except Exception as e:
        return JSONResponse({"error": str(e)}), 500


if __name__ == "__main__":
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
