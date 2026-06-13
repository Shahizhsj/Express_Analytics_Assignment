"""Centralized configuration for shared clients and services."""
import os
from dotenv import load_dotenv
from google import genai
import cohere
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

# Load environment variables from .env file
load_dotenv()

# Google AI Client
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
google_client = genai.Client(
    api_key=GOOGLE_API_KEY
)

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
# Cohere Client
co = cohere.ClientV2(api_key=COHERE_API_KEY)

# Qdrant Client (singleton - shared across app)
client = QdrantClient(path="./qdrant_data")

# Initialize Qdrant collection if it doesn't exist
if not client.collection_exists("documents"):
    client.create_collection(
        collection_name="documents",
        vectors_config=VectorParams(
            size=1024,
            distance=Distance.COSINE
        )
    )

# Auth configuration
SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Upload configuration
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
