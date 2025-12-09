# SchemaLink/core_logic/data_models.py
from pydantic import BaseModel, Field
from typing import List, Dict

class ColumnSchema(BaseModel):
    """Defines metadata for a single database column."""
    name: str = Field(description="The exact column name (e.g., customer_id).")
    data_type: str = Field(description="The SQL data type (e.g., INTEGER, VARCHAR).")
    business_context: str = Field(description="A descriptive, human-readable context for the column, enriched by the auxiliary LLM.")

class ForeignKey(BaseModel):
    """Defines a relationship critical for accurate JOIN generation."""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    description: str = Field(description="Natural language description of the JOIN relationship (e.g., 'Orders is linked to Customers via customer_id').")

class TableSchema(BaseModel):
    """The complete schema unit for a single table, serving as the RAG chunk source."""
    table_name: str
    columns: List[ColumnSchema]
    foreign_keys: List[ForeignKey] = Field(default_factory=list)
    descriptive_text: str = Field(description="The complete text snippet used for RAG retrieval.")

class SchemaRetrievalResult(BaseModel):
    """Structured output from the HybridSearchRetriever."""
    table_name: str
    content: str
    score: float = Field(description="RRF fused score.")
    retrieval_method: str = Field(description="Indicates primary retrieval method for debugging ('Hybrid').")

class SQLGenerationTool(BaseModel):
    """The structured output format the LLM must adhere to when generating SQL."""
    # This acts as the function signature the LLM will be instructed to call
    # when using the 'SQL Generator Tool'.
    query: str = Field(description="The PostgreSQL SELECT or WITH statement, ready for execution.")
    tables_used: List[str] = Field(description="The names of the tables included in the generated query.")
    reasoning: str = Field(description="A brief chain-of-thought explaining why this SQL was generated.")