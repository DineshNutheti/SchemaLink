# SchemaLink/ingestion/introspection.py
from sqlalchemy import create_engine, inspect
from typing import List, Dict
from core_logic.data_models import TableSchema, ColumnSchema, ForeignKey
from config.settings import DB_URI
import logging

ingestion_logger = logging.getLogger('SchemaLink.Introspection')
ingestion_logger.setLevel(logging.INFO)

class DatabaseIntrospectionModule:
    """
    Introspects the target database (PostgreSQL) to extract schema and FK metadata.
    This fulfills the 'Database Introspection Module' requirement in LLD Section 1.
    """
    def __init__(self, db_uri: str = DB_URI):
        # Using the defined read-only URI, but it needs introspection privileges.
        self.engine = create_engine(db_uri)

    def _get_fk_description(self, fk_data: Dict, source_table: str) -> ForeignKey:
        """Helper to format raw FK data into a descriptive string (critical for JOINs)."""
        target_table = fk_data['referred_table']
        source_column = fk_data['constrained_columns'][0]
        target_column = fk_data['referred_columns'][0]
        
        # LLD Focus Point: Foreign Key (FK) Metadata
        desc = (
            f"The '{source_table}' table is linked to the '{target_table}' table "
            f"via the Foreign Key relationship between its column '{source_column}' "
            f"and the target column '{target_column}'."
        )
        return ForeignKey(
            source_table=source_table,
            source_column=source_column,
            target_table=target_table,
            target_column=target_column,
            description=desc
        )

    def _get_table_names(self) -> List[str]:
        """Utility to get all public table names."""
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def _add_business_context(self, col_name: str, raw_context: str) -> str:
        """
        Placeholder for the LLD's 'Schema Description Generation' using a small LLM 
        or a manually curated dictionary to add business context.
        """
        if col_name.lower() == 'prod_cat':
            return "Product category, used for sales reporting and inventory segmentation."
        if col_name.lower() == 'cust_id':
            return "Unique identifier for the customer, used to track loyalty."
        return raw_context

    def _generate_descriptive_text(self, table_name: str, columns: List[ColumnSchema], fks: List[ForeignKey]) -> str:
        """LLD Requirement: Transforms DDL into the RAG descriptive text snippet."""
        col_desc = "\n".join([f"- {c.name} ({c.data_type}): {c.business_context}" for c in columns])
        fk_desc = "\n".join([f"- {fk.description}" for fk in fks])
        
        return f"""
        # Table: {table_name}
        ## Descriptive Schema for SQL Generation
        
        ## Columns and Types:
        {col_desc}
        
        ## Foreign Key Relationships (JOINs):
        {fk_desc if fks else 'No explicit foreign key links defined in schema metadata.'}
        """

    def get_full_schema(self) -> List[TableSchema]:
        """Introspects the entire public schema and generates RAG-ready chunks."""
        inspector = inspect(self.engine)
        table_names = self._get_table_names()
        schema_list = []
        
        ingestion_logger.info(f"Found {len(table_names)} tables for introspection.")

        for table_name in table_names:
            columns_data = inspector.get_columns(table_name)
            fks_data = inspector.get_foreign_keys(table_name)
            
            # 1. Column Metadata + Business Context
            columns = []
            for col in columns_data:
                raw_context = f"Column data type is {str(col['type'])}."
                context = self._add_business_context(col['name'], raw_context)
                columns.append(ColumnSchema(
                    name=col['name'],
                    data_type=str(col['type']),
                    business_context=context
                ))
            
            # 2. FK Metadata
            foreign_keys = [
                self._get_fk_description(fk, table_name) for fk in fks_data
            ]
            
            # 3. Schema Description Generation
            descriptive_text = self._generate_descriptive_text(table_name, columns, foreign_keys)
            
            schema_list.append(TableSchema(
                table_name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
                descriptive_text=descriptive_text
            ))
            
        return schema_list