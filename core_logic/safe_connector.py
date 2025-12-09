# SchemaLink/core_logic/safe_connector.py
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from typing import List, Dict, Union
import logging

security_logger = logging.getLogger('SchemaLink.Security')
security_logger.setLevel(logging.WARNING)

# LLD Requirement: Execution Timeout (5 seconds default)
MAX_QUERY_TIMEOUT_SECONDS = 5 

@event.listens_for(create_engine, "connect")
def set_pg_statement_timeout(dbapi_connection, connection_record):
    """Sets a statement-level timeout on PostgreSQL connections upon creation."""
    cursor = dbapi_connection.cursor()
    # Timeout is set in milliseconds in PostgreSQL
    timeout_ms = MAX_QUERY_TIMEOUT_SECONDS * 1000
    cursor.execute(f"SET statement_timeout = {timeout_ms}")
    cursor.close()

class SafeDatabaseConnector:
    """
    Enforces READ-ONLY access, Statement-Level Timeout, and Hard Stop Guardrail.
    """
    def __init__(self, db_uri: str):
        # NOTE: The provided DB_URI MUST use a user with read-only permissions.
        self.engine = create_engine(db_uri)
        # The timeout listener is attached automatically by SQLAlchemy event system

    def execute_read_only_query(self, sql_query: str) -> List[Dict]:
        """Executes a query after applying security validation and timeout controls."""
        
        # --- 1. Security Check (HARD STOP) ---
        normalized_query = sql_query.strip().upper()
        
        # LLD Resolution: Only SELECT and WITH statements are permitted.
        if not (normalized_query.startswith("SELECT") or normalized_query.startswith("WITH")):
            security_logger.error(f"SECURITY ALERT: Non-SELECT/WITH query attempt: {sql_query}")
            raise PermissionError("Query failed security validation. Only read (SELECT/WITH) statements are allowed.")

        # --- 2. Execution with Timeout & Error Handling ---
        try:
            with self.engine.connect() as connection:
                # Use text() to safely execute the raw SQL string
                result = connection.execute(text(sql_query))
                
                # Convert results to list of dicts for LLM synthesis
                column_names = list(result.keys())
                result_rows = [dict(zip(column_names, row)) for row in result.all()]
                
                return result_rows
                
        except OperationalError as e:
            # LLD: Catch Statement Timeout
            if "statement timeout" in str(e):
                raise TimeoutError(f"Query execution exceeded time limits (>{MAX_QUERY_TIMEOUT_SECONDS}s). Please simplify your request.")
            else:
                # General SQL error for the Self-Correction Loop
                raise ValueError(f"Database Execution Error: {e!r}")
        
        except Exception as e:
            raise RuntimeError(f"A general error occurred during database operation: {e!r}")