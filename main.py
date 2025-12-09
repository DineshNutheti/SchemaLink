# SchemaLink/main.py
import logging
from core_logic.safe_connector import SafeDatabaseConnector
from core_logic.hybrid_retriever import HybridSearchRetriever
from core_logic.llm_agent import LLMAgent
from core_logic.synthesis_module import SynthesisLLM
from ingestion.introspection import DatabaseIntrospectionModule
from ingestion.indexing import SchemaVectorDBIndexer, MockVectorDB, MockKeywordIndex
from config.settings import DB_URI

# Configure basic logging to see the flow
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
main_logger = logging.getLogger('SchemaLink.Main')

# --- 1. System Initialization and Ingestion (Non-Real-Time Setup) ---
def initialize_system(mock_db_uri: str) -> tuple:
    main_logger.info("--- 1. INITIALIZING SCHEMA LINK SYSTEM ---")
    
    # Instantiate Mock Data Stores (Real DBs would be connected here)
    vector_store = MockVectorDB()
    keyword_store = MockKeywordIndex()
    
    # 1a. Introspection (Conceptual: assumes a running Postgres instance for schema)
    # NOTE: Since we are not running a live PG DB, this step is conceptual.
    # We create mock schema data instead of introspecting.
    main_logger.info("Skipping live database introspection. Using simulated schema data.")
    
    # SIMULATED SCHEMA DATA (Based on LLD examples)
    from core_logic.data_models import TableSchema, ColumnSchema, ForeignKey
    
    simulated_schemas = [
        TableSchema(
            table_name="Customers",
            columns=[
                ColumnSchema(name="customer_id", data_type="INT", business_context="Primary key."),
                ColumnSchema(name="customer_name", data_type="VARCHAR", business_context="Full name of the customer."),
                ColumnSchema(name="account_type", data_type="VARCHAR", business_context="e.g., 'Key Account' or 'Standard'.")
            ],
            descriptive_text="# Table: Customers...\nColumns: customer_id, customer_name, account_type."
        ),
        TableSchema(
            table_name="Orders",
            columns=[
                ColumnSchema(name="order_id", data_type="INT", business_context="Primary key."),
                ColumnSchema(name="customer_id", data_type="INT", business_context="FK to Customers table."),
                ColumnSchema(name="total_amount", data_type="NUMERIC", business_context="Total sale amount.")
            ],
            foreign_keys=[
                ForeignKey(source_table="Orders", source_column="customer_id", target_table="Customers", target_column="customer_id", description="Orders links to Customers.")
            ],
            descriptive_text="# Table: Orders...\nColumns: order_id, customer_id, total_amount.\nJOINs: Orders links to Customers via customer_id."
        )
    ]

    # 1b. Indexing
    indexer = SchemaVectorDBIndexer(vector_store, keyword_store)
    indexer.ingest_schema(simulated_schemas)
    
    # 2. Component Wiring (Real-Time Setup)
    db_connector = SafeDatabaseConnector(mock_db_uri)
    retriever = HybridSearchRetriever(vector_store, keyword_store)
    agent = LLMAgent(retriever, db_connector)
    synthesizer = SynthesisLLM()
    
    main_logger.info("--- System Ready. ---")
    return agent, synthesizer

# --- 3. Run Query Function ---
def process_query(agent: LLMAgent, synthesizer: SynthesisLLM, query: str):
    main_logger.info(f"\n--- PROCESSING USER QUERY: '{query}' ---")
    
    # 3a. Run Agent Loop (Retrieval, Generation, Execution, Retry)
    agent_output = agent.run(query)
    
    if agent_output['status'] == 'success':
        main_logger.info(f"SQL SUCCESS: {agent_output['sql_query']}")
        
        # 3b. Synthesis (Scrubbing, Interpretation, Grounding)
        final_answer = synthesizer.synthesize_answer(query, agent_output['result_set'])
        
        main_logger.info("--- FINAL ANSWER ---")
        print(final_answer)
        main_logger.info("--------------------")
        
    else:
        main_logger.error(f"AGENT FAILURE: {agent_output['answer']}")
        print(f"SchemaLink Error: {agent_output['answer']}")


if __name__ == '__main__':
    # NOTE: Set a mock DB URI for demonstration (no live connection needed for this script)
    MOCK_DB_URI = "postgresql+psycopg2://mock_user:mock_pass@127.0.0.1:5432/mock_db"
    
    agent, synthesizer = initialize_system(MOCK_DB_URI)

    # --- SIMULATED TEST CASES ---
    
    # Case 1: Successful Query (requires JOIN)
    # The MockLLMClient will generate the JOIN query here.
    agent.llm_client.error_mode = False 
    process_query(agent, synthesizer, "What was the total order amount for all key accounts?")
    
    # Case 2: Query that fails initially but requires self-correction (MockLLMClient triggers error)
    # The MockLLMClient will return an error query first, then a successful query on retry.
    agent.llm_client.error_mode = True 
    process_query(agent, synthesizer, "What was the total amount of sales across all customers?")
    
    # Case 3: Empty Result Handling
    # We must manually simulate an execution returning an empty list for this test.
    agent.llm_client.error_mode = False
    
    # To test empty results, we temporarily modify the LLMAgent execution to force empty data:
    def execute_mock_empty(self, sql_query: str) -> List[Dict]:
        return [] # Force empty result

    # Temporarily patch the method
    agent.db_connector.execute_read_only_query = execute_mock_empty.__get__(agent.db_connector, SafeDatabaseConnector)
    process_query(agent, synthesizer, "Show me all orders from Antarctica.")
    
    # Reset the mock method to original to prevent contamination
    # (This demonstrates why good testing is crucial!)