import os
import io
import torch
import psycopg2
from PIL import Image
from pgvector.psycopg2 import register_vector
import clip
from dotenv import load_dotenv
from nameExtractor import name_extractor

# Load environment variables from .env file
load_dotenv()

# Configuration
DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"), # Default PostgreSQL port
}

DB_TABLE = os.getenv("DB_Table")

TOP_K = os.getenv("TOP_K")  # Number of search results to return


# CLIP Encoder Initialization
try:
    # Use a standard 768-dimension model like ViT-L/14
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    MODEL,PROCESSOR = clip.load("ViT-L/14", device=DEVICE)
    print(f"CLIP Model loaded successfully on {DEVICE}.")
except Exception as e:
    print(f"Error loading CLIP model: {e}")
    MODEL = None
    PROCESSOR = None

# Get Database Connection
def get_db_connection():
    """Establishes and returns a database connection."""
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    register_vector(conn) # Register vector type for psycopg2
    return conn, cursor

def get_query_embedding(image_bytes):
    """Encodes the user's uploaded image into a vector."""
    if not MODEL or not PROCESSOR:
        raise RuntimeError("CLIP model failed to load.")
        
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # CLIP's preprocessor from clip.load() returns a tensor directly
    image_input = PROCESSOR(image).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        # Use encode_image for models loaded with clip.load()
        image_features = MODEL.encode_image(image_input)
    
    # Normalize and convert to list for pgvector
        embedding = image_features.cpu().numpy().flatten().tolist()
        
    return embedding

# Perform Vector Search
def perform_vector_search(phone_model,query_vector):
    """Queries the PostgreSQL pgvector table for similar products."""
    conn = None
    try:
        conn,cur = get_db_connection()
        
        # phone_modal = name_extractor("phonemodal.csv",phone_modal)
        phone_model = name_extractor("phonemodal.csv",phone_model)
        print("Phone Model after extraction:",phone_model)
        # SQL Query: Use the <=> operator for Cosine Distance/Similarity
        # We order by distance ASC (closer to 0 is more similar) and limit to TOP_K
        # We use the ::vector cast to explicitly tell PostgreSQL that the query vector is a vector
        Search_query = """
                    SELECT 
                        name, 
                        price, 
                        image_url,
                        model,
                        (embedding <=> %s::vector) AS cosine_distance 
                    FROM shopify_products 
                     WHERE model = %s   
                    ORDER BY cosine_distance ASC 
                    LIMIT %s;
                    """
        

        # The query vector is passed as a list, which pgvector handles
        cur.execute(Search_query, (query_vector,phone_model['phone_model'], TOP_K))
        result = cur.fetchall()
        if result:
            for row in result:
                name, price, image_url, model, distance = row
                
                # Convert cosine distance (0=same, 2=opposite) to similarity (1=same, -1=opposite)
                # Similarity = 1 - distance (for the standard pgvector <=> operator range)
                # The actual distance range is 0 to 2, so 1 - distance/2 is more accurate for 0..1 scale
                similarity = 1 - (distance / 2)

                if similarity >= 0.85:
                    return {
                        "name": name,
                        "image_url": image_url,
                        "Phone_Model": model,
                        "Link": "https://ollypolly.in/search?q=" + (name.replace(" ", "+") if name else ""),
                    },200
                else:
                    phone_model_name = phone_model.get('phone_model') or "Unknown"
                    return {
                        "name": phone_model['phone_model'],
                        "image_url": None,
                        "Phone_Model": model,
                        "Link": "https://ollypolly.in/search?q=" + phone_model_name.replace(" ", "+"),
                    },200

        else:
            phone_model_name = phone_model.get('phone_model') or "Unknown"
            print("error wala yaher per",phone_model_name)
            return {
                "name": phone_model['phone_model'],
                "image_url": None,
                "Phone_Model": phone_model['phone_model'],
                "Link": "https://ollypolly.in/search?q=" + phone_model_name.replace(" ", "+"),
            },200
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return {"error": "Database query failed"}, 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": "Internal server error"}, 500
    finally:
        if conn:
            conn.close()

