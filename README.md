# Final CLIP Model Project

This project implements a CLIP (Contrastive Language-Image Pretraining) based image search system for finding similar phone cases and accessories on the OllyPolly.in e-commerce platform. It uses vector embeddings to perform semantic search on product images.

## Project Overview

The system consists of several components that work together to provide an AI-powered product recommendation service based on user-uploaded images.

## Files and Their Roles

### Core Application Files

#### `app.py`
- **Purpose**: Main FastAPI web application server
- **Functionality**:
  - Provides REST API endpoints for image-based product search
  - Handles image URL processing and vector search requests
  - Returns similar product recommendations with links
- **Key Endpoints**:
  - `GET /`: Health check endpoint
  - `GET /image_link/`: Main search endpoint accepting `phone_modal` and `image_url` parameters
- **Usage**: Run with `python app.py` to start the server on localhost:8000

#### `OllypollyAi.py`
- **Purpose**: Contains the core AI and database search logic
- **Functionality**:
  - Initializes CLIP model (ViT-L/14) for image encoding
  - `get_query_embedding()`: Converts user-uploaded images to 768-dimensional vectors
  - `perform_vector_search()`: Queries PostgreSQL database using pgvector for cosine similarity search
  - Filters results by phone model and similarity threshold (≥0.85)
- **Dependencies**: CLIP, PyTorch, PostgreSQL with pgvector extension

#### `manage.py`
- **Purpose**: Data ingestion and management script
- **Functionality**:
  - Fetches product inventory from external API
  - Downloads and encodes product images using CLIP
  - Stores product data and embeddings in PostgreSQL database
  - Handles bulk data ingestion with proper error handling
- **Usage**: Run periodically to update product catalog

#### `scheduler.py`
- **Purpose**: Automated task scheduler
- **Functionality**:
  - Runs daily data ingestion (`manage.py`)
  - Updates phone model CSV file (`nameExtractor.py`)
  - Designed to run as a background service at 4 AM
- **Usage**: Execute as a cron job or scheduled task

### Utility Files

#### `nameExtractor.py`
- **Purpose**: Phone model name processing and extraction
- **Functionality**:
  - `name_saver()`: Extracts unique phone models from database and saves to CSV
  - `name_extractor()`: Uses OpenAI GPT-4 to match user input to standardized phone model names
  - Contains extensive local dictionary of phone model variations
- **Dependencies**: OpenAI API, PostgreSQL

#### `phonemodal.csv`
- **Purpose**: Data file containing all available phone models
- **Content**: Comma-separated list of phone model names extracted from the database
- **Usage**: Used by `nameExtractor.py` for fuzzy matching of user input

#### `requirements.txt`
- **Purpose**: Python dependencies specification
- **Key Dependencies**:
  - `fastapi`: Web framework
  - `clip`: OpenAI's CLIP model
  - `torch`: PyTorch for model inference
  - `pgvector`: PostgreSQL vector extension
  - `openai`: For phone model matching
  - `psycopg2`: PostgreSQL driver
  - Other supporting libraries (PIL, requests, etc.)

## System Flow

1. **Data Ingestion** (`scheduler.py` → `manage.py`):
   - Fetch product catalog from external API
   - Download product images
   - Generate CLIP embeddings for each image
   - Store product data and vectors in PostgreSQL

2. **Model Update** (`scheduler.py` → `nameExtractor.py`):
   - Extract unique phone models from database
   - Save to `phonemodal.csv` for reference

3. **User Query Processing** (`app.py` → `OllypollyAi.py`):
   - Receive image URL and phone model from user
   - Download and encode user image with CLIP
   - Match phone model using OpenAI/fuzzy matching
   - Perform vector similarity search in database
   - Return top matching product with link

## Database Schema

The system uses PostgreSQL with the pgvector extension:

```sql
CREATE TABLE shopify_products (
    name TEXT,
    price DECIMAL,
    image_url TEXT,
    model TEXT,
    embedding vector(768)  -- CLIP embedding
);
```

## Environment Variables

Required environment variables (stored in `.env` file):
- `DB_NAME`: PostgreSQL database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `DB_TABLE`: Database table name
- `TOP_K`: Number of search results to return
- `OPENAI_API_KEY`: OpenAI API key for phone model matching
- `API_LINK`: External API URL for product data

## Installation and Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**:
   - Install PostgreSQL with pgvector extension
   - Create database and table
   - Configure environment variables

3. **Initial Data Ingestion**:
   ```bash
   python manage.py
   python scheduler.py
   ```

4. **Run Application**:
   ```bash
   python app.py
   ```

## API Usage

### Search for Similar Products

**Endpoint**: `GET /image_link/`

**Parameters**:
- `phone_modal` (string): Phone model name (e.g., "iPhone 15", "15 pro max", "Samsung Galaxy S23")
- `image_url` (string): URL of the image to search for similar products

**Example Request**:
```
GET /image_link/?phone_modal=15%20pro%20max&image_url=https://bot-data.s3.ap-southeast-1.wasabisys.com/upload/2026/1/livechat/177923-287915-907159858538302.jpeg
```

**Example Input**:
- Phone Model: "15 pro max"
- Image: See `input.jpeg` in the project directory for a sample input image

**Example Output**:
```json
{
  "Name:": "Anime With In-Built Stand Cover For  iPhone 15 Pro Max",
  "Link:": "https://ollypolly.in/search?q=Anime+With+In-Built+Stand+Cover+For++iPhone+15+Pro+Max"
}
```

**Response Fields**:
- `Name:`: Product name of the best matching result
- `Link:`: Direct search URL on OllyPolly.in for the product

**Notes**:
- The system uses fuzzy matching for phone model names
- Returns the most similar product with similarity score ≥ 0.85
- If no close match is found, returns a general search link for the phone model
- Image URL must be publicly accessible

### Additional Files

#### `input.jpeg`
- **Purpose**: Sample input image for testing the API
- **Usage**: Example image that can be used to test the similarity search functionality

#### `input_process_output.csv`
- **Purpose**: Contains example API inputs and expected outputs for testing
- **Content**: Demonstrates the request format and response structure

## Technologies Used

- **AI/ML**: CLIP (ViT-L/14), PyTorch
- **Backend**: FastAPI, Python
- **Database**: PostgreSQL with pgvector
- **APIs**: OpenAI GPT-4, External product API
- **Image Processing**: PIL (Pillow)

## Deployment

- Designed for deployment as a web service
- Scheduler can run as a cron job or containerized service
- Requires GPU access for optimal CLIP performance (falls back to CPU)</content>
<parameter name="filePath">/Users/parthmishra/Desktop/Final clip model/README.md