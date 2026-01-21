import os
import requests
import torch
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from PIL import Image
from io import BytesIO
import dotenv

dotenv.load_dotenv()

device = "cuda" if torch.cuda.is_available() else "cpu"

#Configuration
DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT") # Default PostgreSQL port
}

EMBEDDING_DIM = 768 # output size of CLIP model

# Mock Data Source
def fetch_inventory_data():
    """Simulates fetching product data from a master API."""
    data = requests.get(os.getenv("API_LINK"))
    i = 0
    result = []
    for items in data.json():
            if items['image_url'] != None and items['shopify'] != "No":
                if items['shopifyName'][0]['name']:
                    if items['model'] != []:
                        result.append(items)
    return result
    # return [
    #     {"product_id": "P001", "name": "Metal Series Magsafe Leather Case With Titanium Frame", "price": 49.99,"shortcut": "IP 16+", "image_url": "https://ollypolly.in/cdn/shop/files/main_upload.jpg?v=1739625318&width=1200"},
    #     {"product_id": "P002", "name": "Luxury MagSafe Leather Case for Samsung Galaxy Z Fold 7 – Executive Edition with Magnetic Ring & Precision Fit", "price": 79.50,"shortcut": "IP 16+", "image_url": "https://ollypolly.in/cdn/shop/files/47.jpg?v=1762582407&width=1200"},
    # ]

# 1. CLIP Encoder Setup (Reusing your previous logic)
def get_clip_model():
    import clip
    clip_model, preprocess = clip.load(
    "ViT-L/14", device=device)
    return clip_model,preprocess  

MODEL, PROCESSOR = get_clip_model()

def get_image_embedding(image_bytes):
    """Encodes the image bytes into a 768-dimension vector"""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB") # Ensure image is RGB
        
        # Pass the PIL Image directly to PROCESSOR.
        # It returns a transformed PyTorch Tensor.
        image_input_tensor = PROCESSOR(image).unsqueeze(0).to(device)
        
        # 2.Use model.encode_image() for the model loaded via clip.load()
        with torch.no_grad():
            image_features = MODEL.encode_image(image_input_tensor)
        
        # Normalize and convert to list/numpy array for insertion
        # Note: CLIP often normalizes features internally, but explicit normalization is good practice
        # image_features /= image_features.norm(dim=-1, keepdim=True) 
        embedding = image_features.cpu().numpy().flatten().tolist()
        return embedding
    except Exception as e:
        # Re-raise the exception or print detailed info for debugging
        print(f"Error encoding image: {e}") 
        return None
      
def ingest_data():
    conn = None
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Register the vector type with psycopg2 for easy insertion
        register_vector(conn)
        
        # Delete existing data
        cur.execute("DELETE FROM shopify_products;")
        conn.commit()
        
        inventory_data = fetch_inventory_data()
        records_to_insert = []
        
        print(f"Starting ingestion of {len(inventory_data)} products...")

        # Bulk extract Image embed
        for item in inventory_data:
            image_url = item['image_url']
            
            # Download image bytes directly for encoding
            response = requests.get(image_url, stream=True,timeout=30)

            if response.status_code != 200:
                print(f"Skipping {item['idProduct']}: Failed to download image from {image_url}")
                continue

            image_bytes = response.content
            
            # Generate Embedding
            embedding = get_image_embedding(image_bytes)
            
            for i in range(len(item['model'])):
                model = item['model'][i]
                
                if embedding:
                    # Prepare a tuple for bulk insertion
                    record = (
                            item['shopifyName'][0]['name'],
                            item['price'],
                            item['image_url'],
                            model,
                            embedding,
                            item['productCode']+'-'+str(i)
                      )

                    records_to_insert.append(record)
            print(f"Processed {item['productCode']}")
            # print("records_to_insert:",records_to_insert)
        # Insert all records at once (OUTSIDE THE LOOP)
        if records_to_insert:
            insert_query = """
            INSERT INTO shopify_products (name, price, image_url, model, embedding,productcode)
            VALUES %s
            ON CONFLICT (id) DO UPDATE 
            SET 
            name = EXCLUDED.name, 
            price = EXCLUDED.price, 
            image_url = EXCLUDED.image_url,
            model = EXCLUDED.model,
            embedding = EXCLUDED.embedding,
            productcode = EXCLUDED.productcode;
            """

            # execute_values is much faster for bulk inserts
            execute_values(cur, insert_query, records_to_insert, page_size=100)
            
            # COMMIT THE TRANSACTION - THIS IS CRITICAL!
            conn.commit()
            print(f"✓ Successfully committed {len(records_to_insert)} records to PostgreSQL.")
        else:
            print("No records to insert.")

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL or during ingestion:", error)
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()
            print("PostgreSQL connection closed.")

if __name__ == "__main__":
    ingest_data()
    # fetch_inventory_data()

