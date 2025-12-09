# SchemaLink/core_logic/hybrid_retriever.py
import numpy as np
from typing import List, Dict, Union, Tuple
from collections import defaultdict
# Import constants from settings
from config.settings import K_SEARCH, RRF_K, TOKEN_BUDGET
# Import data models for type hinting/structure
from core_logic.data_models import SchemaRetrievalResult
import logging
# Import the actual mock connectors from the ingestion module
from ingestion.indexing import MockVectorDB, MockKeywordIndex 

retrieval_logger = logging.getLogger('SchemaLink.Retrieval')
retrieval_logger.setLevel(logging.INFO)


# --- Utility Function: Reciprocal Rank Fusion (RRF) ---
# LLD Requirement: RRF to combine Vector (Semantic) and Keyword (Lexical) ranks.

def reciprocal_rank_fusion(
    search_results: List[List[str]], # List of ranked document IDs (e.g., table names)
    k: int = RRF_K
) -> List[str]:
    """
    Applies Reciprocal Rank Fusion to a list of ranked search results.
    RRF(d) = Σ [ 1 / (k + rank(d)) ]
    """
    fused_scores = defaultdict(float)
    
    # search_results is a list of ranking lists (e.g., [vector_ranks, keyword_ranks])
    for ranks in search_results:
        for rank, doc_id in enumerate(ranks):
            # Rank starts at 0, so the position is rank + 1
            score = 1.0 / (k + rank + 1)
            fused_scores[doc_id] += score
            
    # Sort documents by the fused score in descending order
    sorted_docs = sorted(
        fused_scores.keys(), 
        key=lambda doc_id: fused_scores[doc_id], 
        reverse=True
    )
    
    return sorted_docs

# --- Core Module: HybridSearchRetriever ---

class HybridSearchRetriever:
    """
    Implements the core RAG retrieval logic for SchemaLink.
    Performs parallel vector and keyword searches, then fuses results via RRF.
    """
    def __init__(self, vector_db_connector: MockVectorDB, keyword_index_connector: MockKeywordIndex):
        # The connectors are now instantiated MockDB objects from the Indexer
        self.vector_db = vector_db_connector     
        self.keyword_index = keyword_index_connector 
        self.k_search = K_SEARCH
        self.k_rrf = RRF_K       

    def _semantic_search(self, query: str) -> List[str]:
        """Calls the actual vector search simulation in the MockVectorDB."""
        # Now calls the dynamic method on the Mock object
        return self.vector_db.query_top_k(query, self.k_search)

    def _keyword_search(self, query: str) -> List[str]:
        """Calls the actual keyword search simulation in the MockKeywordIndex."""
        # Now calls the dynamic method on the Mock object
        return self.keyword_index.query_top_k(query, self.k_search)
    
    def _fetch_full_schema_content(self, table_name: str) -> str:
        """Fetches the full schema text chunk from the Vector DB store."""
        # Now calls the dynamic method on the Mock object
        content = self.vector_db.get_content(table_name)
        if not content:
             retrieval_logger.error(f"Schema content not found for table: {table_name}")
             # LLD Fallback: Semantic Mismatch resolution is handled by RRF and fallback retrieval.
             # If content is truly missing here, it means the ingestion failed, or the table doesn't exist.
             return f"# Table: {table_name}\nError: Schema content missing from index."
        return content

    # LLD Requirement: Implement Hybrid Search & Context Window Optimization
    def retrieve_schema_chunks(self, query: str) -> Tuple[List[Dict[str, str]], bool]:
        """
        Executes hybrid search, fuses ranks, and aggregates content respecting the token budget.
        
        Returns: 
          - List of dictionaries: [{'table_name': 'X', 'content': 'Schema text...'}]
          - Truncation warning flag (bool)
        """
        retrieval_logger.info(f"Starting Hybrid Retrieval for query: '{query[:40]}...'")
        
        # 1. Parallel Searches
        vector_ranks = self._semantic_search(query)
        keyword_ranks = self._keyword_search(query)
        
        # 2. RRF Fusion
        fused_ranks = reciprocal_rank_fusion([vector_ranks, keyword_ranks], k=self.k_rrf)
        retrieval_logger.info(f"RRF Fused Ranks (Top {len(fused_ranks)}): {fused_ranks}")
        
        # 3. Context Window Optimization (Aggregation and Truncation)
        current_token_count = 0
        retrieved_context = []
        truncation_warning = False
        
        for table_name in fused_ranks:
            # Fetch content dynamically using the mock store
            schema_content = self._fetch_full_schema_content(table_name)
            
            # Simple token estimation (approx 1 token = 4 characters)
            content_tokens = len(schema_content) // 4 
            
            if current_token_count + content_tokens <= TOKEN_BUDGET:
                retrieved_context.append({'table_name': table_name, 'content': schema_content})
                current_token_count += content_tokens
            else:
                # LLD Resolution: If truncation occurs, set a warning flag.
                truncation_warning = True
                retrieval_logger.warning(f"Schema context truncated. Budget exceeded ({current_token_count}/{TOKEN_BUDGET} tokens).")
                break # Stop adding more chunks

        return retrieved_context, truncation_warning