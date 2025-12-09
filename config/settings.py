# SchemaLink/config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file (optional, but good practice)
load_dotenv()

# --- Database Configuration (LLD Section 2) ---
# NOTE: This URI MUST point to a user with READ-ONLY permissions on a PostgreSQL DB.
DB_URI = os.getenv("SCHEMA_LINK_DB_URI", "postgresql+psycopg2://readonly_user:password@localhost:5432/schemalink_db")
MAX_QUERY_TIMEOUT_SECONDS = 5  # LLD Requirement: Statement-level timeout

# --- LLM and Agent Configuration ---
# LLM used for SQL Generation, Self-Correction, and Synthesis
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o") 
LLM_API_KEY = os.getenv("LLM_API_KEY") # Ensure this is loaded securely

# --- RAG/Retrieval Configuration (LLD Section 1 & 2) ---
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2" # Vectorization Consistency
K_SEARCH = 10                  # Top K results from individual Vector/Keyword searches
RRF_K = 60                     # RRF hyperparameter for rank fusion
TOKEN_BUDGET = 500             # LLD Requirement: Context Window Optimization (Hard limit for retrieved schema)

# --- Agent Control Configuration (LLD Section 2) ---
MAX_RETRY_COUNT = 1            # LLD Requirement: Robust Retry Loop (limit: 1)
SQL_START_TOKEN = "[SQL_START]" # LLD Requirement: Robust parsing tokens
SQL_END_TOKEN = "[SQL_END]"