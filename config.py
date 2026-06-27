import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# API Keys definition
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# LLM model settings
LLM_MODEL = "gemini-3.1-flash-lite"
STUDY_TOOLS_MODEL = "gemini-3.1-flash-lite"
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSION = 3072

# Document chunking config
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 50

# RAG search retrieval
TOP_K_RETRIEVAL = 20
TOP_K_RERANK = 5
HYBRID_ALPHA = 0.7

# Chat history settings
MAX_CONVERSATION_TURNS = 10
MAX_CONTEXT_LENGTH = 8000

# Directory storage paths
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")

# Local server details
HOST = "127.0.0.1"
PORT = 8000

# Create upload paths
os.makedirs(CHROMA_DB_PATH, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
