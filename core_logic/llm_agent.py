# SchemaLink/core_logic/llm_agent.py
import re
import time
from typing import List, Dict, Tuple, Optional
import logging

from config.settings import (
    LLM_MODEL_NAME, SQL_START_TOKEN, SQL_END_TOKEN, 
    MAX_RETRY_COUNT, TOKEN_BUDGET
)
from config.prompts import (
    SYSTEM_PROMPT_TEMPLATE, CRITIC_PROMPT_TEMPLATE
)
from core_logic.safe_connector import SafeDatabaseConnector
from core_logic.hybrid_retriever import HybridSearchRetriever
from core_logic.data_models import SQLGenerationTool

agent_logger = logging.getLogger('SchemaLink.Agent')
agent_logger.setLevel(logging.INFO)

# --- Conceptual LLM Client ---
class MockLLMClient:
    """Simulates the API calls to an external LLM (e.g., GPT-4o)."""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.error_mode = False # Controls simulated failure

    def generate(self, prompt: str) -> str:
        """Simulates LLM call and returns a generated response."""
        
        # Simple error simulation for testing the self-correction loop
        if self.error_mode:
            self.error_mode = False # Reset for the next call (the retry)
            # Simulate a query with a non-existent column to force a DB error
            return f"{SQL_START_TOKEN}SELECT non_existent_column FROM Orders;{SQL_END_TOKEN}"
        
        # Simulate a successful query based on prompt content
        if "key accounts" in prompt:
            sql = "SELECT T1.total_amount, T2.customer_name FROM Orders T1 JOIN Customers T2 ON T1.customer_id = T2.customer_id WHERE T2.account_type = 'Key Account';"
        else:
            sql = "SELECT SUM(total_amount) FROM Orders;"
            
        return f"{SQL_START_TOKEN}{sql}{SQL_END_TOKEN}"

# --- Prompt Builder ---
class DynamicPromptBuilder:
    """
    Assembles the final prompt for the LLM based on retrieved context.
    Fulfills the Dynamic Prompt Builder requirement.
    """
    def __init__(self):
        pass

    def build_sql_prompt(self, user_query: str, schema_context_list: List[Dict], is_retry: bool = False, error_details: Optional[Dict] = None) -> str:
        """Constructs the prompt, either for initial generation or for self-correction."""
        
        # Combine schema chunks into a single string
        schema_context_str = "\n".join([chunk['content'] for chunk in schema_context_list])
        
        if is_retry and error_details:
            # LLD Requirement: Feed error message back to LLM (for retry)
            prompt = CRITIC_PROMPT_TEMPLATE.format(
                failed_query=error_details['query'],
                error_message=error_details['error']
            )
            # Add schema context after the error details for the LLM to re-evaluate
            prompt += f"\n--- SCHEMA CONTEXT (Original) ---\n{schema_context_str}"
            prompt += f"\n--- USER QUESTION (Original) ---\n{user_query}"
        else:
            # Initial generation prompt
            prompt = SYSTEM_PROMPT_TEMPLATE.format(
                schema_context=schema_context_str
            )
            prompt += f"\n--- USER QUESTION ---\n{user_query}"
        
        return prompt

# --- Core Agent Logic ---
class LLMAgent:
    """Manages the agentic loop, tool calling, and self-correction."""
    
    def __init__(self, retriever: HybridSearchRetriever, db_connector: SafeDatabaseConnector):
        self.retriever = retriever
        self.db_connector = db_connector
        self.llm_client = MockLLMClient(LLM_MODEL_NAME)
        self.prompt_builder = DynamicPromptBuilder()

    def _parse_sql(self, response_text: str) -> Optional[str]:
        """
        Parses the LLM's response to extract the SQL query.
        Uses the specified start/end tokens for robust parsing (LLD requirement).
        """
        pattern = re.escape(SQL_START_TOKEN) + r"\s*(.*?)\s*" + re.escape(SQL_END_TOKEN)
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            # Strip extra quotes or newlines often added by LLMs
            return match.group(1).strip().replace("`", "") 
        return None

    def _generate_sql(self, user_query: str, schema_context: List[Dict], attempt: int, error_details: Optional[Dict] = None) -> Tuple[Optional[str], str]:
        """Generates SQL using the LLM and prompt builder."""
        
        is_retry = (attempt > 0)
        prompt = self.prompt_builder.build_sql_prompt(user_query, schema_context, is_retry, error_details)
        
        start_time = time.time()
        # LLD Requirement: Tool Specification (LLM is commanded to output SQL)
        response_text = self.llm_client.generate(prompt)
        generation_latency = time.time() - start_time
        
        agent_logger.info(f"Attempt {attempt} SQL Generation Latency: {generation_latency:.2f}s")
        
        sql_query = self._parse_sql(response_text)
        
        if not sql_query:
            agent_logger.error(f"Failed to parse SQL from LLM response in attempt {attempt}.")
            return None, response_text # Return None for SQL, original text for debugging

        return sql_query, response_text

    def run(self, user_query: str) -> Dict:
        """
        The main Agentic Reasoning & Retrieval Loop.
        Manages the retrieval, generation, execution, and self-correction.
        """
        full_result = {"status": "failure", "answer": "Could not generate or execute a valid query."}
        
        # 1. Retrieval Latency (LLD Monitoring)
        start_time_retrieval = time.time()
        schema_context, truncation_warning = self.retriever.retrieve_schema_chunks(user_query)
        retrieval_latency = time.time() - start_time_retrieval
        agent_logger.info(f"Retrieval Latency: {retrieval_latency:.2f}s. Truncation Warning: {truncation_warning}")

        if not schema_context:
            return {"status": "failure", "answer": "Schema retrieval failed. Context is empty."}
        
        # 2. SQL Generation and Execution Loop (LLD Retry Loop)
        for attempt in range(MAX_RETRY_COUNT + 1):
            error_details = full_result.get('error_details')
            
            sql_query, llm_response = self._generate_sql(user_query, schema_context, attempt, error_details)
            
            if not sql_query:
                full_result['answer'] = f"LLM failed to generate parseable SQL after {attempt} attempts."
                continue # Try next attempt if available (should only happen if retry fails too)

            # 3. Execution Latency (LLD Monitoring)
            start_time_execution = time.time()
            try:
                # Executes query with Hard Stop, Read-Only, and Timeout guardrails
                result_set = self.db_connector.execute_read_only_query(sql_query)
                execution_latency = time.time() - start_time_execution
                agent_logger.info(f"Execution Latency: {execution_latency:.2f}s")

                # Successful execution! Break the loop and proceed to synthesis.
                full_result.update({
                    "status": "success",
                    "sql_query": sql_query,
                    "result_set": result_set,
                    "total_latency_s": retrieval_latency + execution_latency + full_result.get('generation_latency', 0)
                })
                break
                
            except (ValueError, PermissionError, TimeoutError) as e:
                # Handles LLD Errors: SQL Syntax/Semantic Error (ValueError), Security (PermissionError), Timeout (TimeoutError)
                
                error_message = str(e)
                agent_logger.warning(f"Execution failed on attempt {attempt}: {error_message[:100]}")

                if isinstance(e, PermissionError):
                    # LLD: Security Guardrail Bypass - immediate failure.
                    return {"status": "failure", "answer": f"Query execution terminated by security guardrail: {error_message}"}
                
                if isinstance(e, TimeoutError):
                    # LLD: Execution Timeout - immediate failure.
                    return {"status": "failure", "answer": error_message}

                # Store error details for the Self-Correction Loop
                full_result['error_details'] = {"query": sql_query, "error": error_message}
                
                if attempt == MAX_RETRY_COUNT:
                    full_result['answer'] = f"SQL failed execution after max retries. Final error: {error_message}"
                    break
                    
                # If retry is available, the loop continues (Self-Correction)

        return full_result