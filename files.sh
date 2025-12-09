#!/bin/bash

PROJECT_ROOT="/home/dinesh/Documents/SchemaLink"

# Create main directories
mkdir -p $PROJECT_ROOT/config
mkdir -p $PROJECT_ROOT/core_logic
mkdir -p $PROJECT_ROOT/ingestion

# Create top-level files
touch $PROJECT_ROOT/main.py

# Create config files
touch $PROJECT_ROOT/config/settings.py
touch $PROJECT_ROOT/config/prompts.py

# Create core_logic files
touch $PROJECT_ROOT/core_logic/__init__.py
touch $PROJECT_ROOT/core_logic/data_models.py
touch $PROJECT_ROOT/core_logic/safe_connector.py
touch $PROJECT_ROOT/core_logic/hybrid_retriever.py
touch $PROJECT_ROOT/core_logic/llm_agent.py
touch $PROJECT_ROOT/core_logic/synthesis_module.py

# Create ingestion files
touch $PROJECT_ROOT/ingestion/__init__.py
touch $PROJECT_ROOT/ingestion/introspection.py
touch $PROJECT_ROOT/ingestion/indexing.py
touch $PROJECT_ROOT/ingestion/auxiliary_llm.py

echo "SchemaLink project structure created successfully."