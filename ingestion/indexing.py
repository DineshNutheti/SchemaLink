# SchemaLink/ingestion/indexing.py
from typing import List, Dict, Union
from core_logic.data_models import TableSchema
from config.settings import EMBEDDING_MODEL_NAME
import logging

indexing_logger = logging.getLogger('SchemaLink.Indexing')
indexing_logger.setLevel(logging.INFO)

# --- Conceptual Connectors for Demonstration ---
# In a real system, these would be ChromaDB/Pinecone/Elasticsearch clients.

class MockVectorDB:
    """Simulates the Vector Database storing schema embeddings."""
    def __init__(self):
        # Key: Table Name, Value: (Vector, Metadata/Content)
        self._store: Dict[str, str] = {}
        indexing_logger.info("MockVectorDB initialized.")
    
    def add(self, table_name: str, content: str):
        # Simulates embedding (vector generation) and storage
        self._store[table_name] = content
        # Note: In a real system, the vector is what's queried, but here we store the content directly.

    def query_top_k(self, query: str, k: int) -> List[str]:
        """Simulates semantic search, returning a ranked list of table names."""
        # For a mock, we return a predetermined semantic ranking (based on conceptual similarity)
        # This simulates the LLM asking about 'sales' being semantically close to 'Orders' and 'Products'.
        if 'sales' in query.lower() or 'revenue' in query.lower():
            return ['Orders', 'Products', 'Customers', 'Shipments']
        elif 'user' in query.lower() or 'account' in query.lower():
            return ['Customers', 'Orders', 'SalesLogs', 'Employees']
        else:
            return list(self._store.keys())[:k] # Fallback

    def get_content(self, table_name: str) -> str:
        """Retrieves the full content text for a given table."""
        return self._store.get(table_name, "")


class MockKeywordIndex:
    """Simulates a Lexical/Keyword Index (e.g., BM25) for column/table names."""
    def __init__(self):
        # Key: Table Name, Value: Content (optional, often just stores IDs)
        self._store: Dict[str, str] = {}
        indexing_logger.info("MockKeywordIndex initialized.")

    def add(self, table_name: str, content: str):
        # Simulates indexing the text fields for keyword search
        self._store[table_name] = content

    def query_top_k(self, query: str, k: int) -> List[str]:
        """Simulates keyword search, returning a ranked list of table names."""
        # Simulates finding exact matches (Lexical)
        
        # Example simulation: if query contains 'customer_id' (a keyword match)
        if 'id' in query.lower() or 'customer' in query.lower():
            return ['Customers', 'Orders', 'Employees', 'Shipments']
        elif 'amount' in query.lower():
            return ['Orders', 'Products', 'SalesLogs', 'Customers']
        else:
            return list(self._store.keys())[::-1][:k] # Reverse order fallback (simulates different ranking)


class SchemaVectorDBIndexer:
    """
    Handles indexing the descriptive schema text into the Vector DB and Keyword Index.
    Fulfills the 'Vectorization Consistency' requirement.
    """
    def __init__(self, vector_db: MockVectorDB, keyword_index: MockKeywordIndex, embedding_model_name: str = EMBEDDING_MODEL_NAME):
        # LLD Requirement: Enforce consistency in embedding model name
        self.embedding_model_name = embedding_model_name
        self.vector_db = vector_db
        self.keyword_index = keyword_index
        indexing_logger.info(f"Indexer initialized for model: {self.embedding_model_name}")

    def ingest_schema(self, schemas: List[TableSchema]):
        """Indexes all schema chunks into the RAG sources."""
        indexing_logger.info(f"Starting ingestion of {len(schemas)} schema documents.")
        
        for s in schemas:
            # 1. Vector Indexing (Semantic)
            self.vector_db.add(s.table_name, s.descriptive_text)
            
            # 2. Keyword Indexing (Lexical)
            self.keyword_index.add(s.table_name, s.descriptive_text)

        indexing_logger.info("Schema ingestion complete.")