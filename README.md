# SchemaLink: Natural Language to Database Query Agent

## ✨ Overview

The **SchemaLink** project is an advanced AI Agent designed to democratize access to complex relational databases. By leveraging a **Retrieval-Augmented Generation (RAG)** pipeline, it accurately translates user questions expressed in plain English into secure, executable SQL queries. This system eliminates the need for manual SQL composition, making data analysis accessible to non-technical users while ensuring query precision through contextual schema retrieval.

### 🎯 Key Goals

  * **Democratize Data Access:** Enable all users to retrieve data without knowing SQL syntax.
  * **Enhance Accuracy:** Use RAG to inject only the most relevant schema context, minimizing LLM hallucination and improving query reliability.
  * **Ensure Security:** Execute queries using strictly read-only connections and validate SQL structure before execution.

-----

| Component | Role | Technology Stack |
| :--- | :--- | :--- |
| **Backend API** | Handles user requests, manages agent orchestration, and hosts the RAG pipeline. | **Python, FastAPI** |
| **Data Connector** | Introspects the target database and connects for query execution. | **SQLAlchemy** |
| **Vector Store** | Stores vectorized metadata (schema, column descriptions, relationships) for semantic retrieval. | **ChromaDB / Pinecone** |
| **Agent Framework** | Facilitates prompt engineering, tool calling, and multi-step reasoning workflow. | **LangChain / LlamaIndex** |
| **LLM** | The core reasoning engine for translating NL context to SQL and summarizing results. | **Gemini API / OpenAI** |

-----

That's a great idea\! Presenting the project's file structure early in the `README` helps developers and users quickly grasp the system's architecture and where key logic resides.

Here is the finalized project tree structure and a template for the `README.md` that incorporates this structure along with key explanations.

-----

## 🏗️ SchemaLink Project Structure

```
SchemaLink/
├── config/
│   ├── settings.py           # ⚙️ Environment Variables (DB_URI, API Keys), Hyperparameters (TOKEN_BUDGET, RRF_K).
│   └── prompts.py            # 📝 All LLM Prompt Templates (System, SQL Critic, Synthesis, Empty Result).
├── core_logic/
│   ├── __init__.py
│   ├── data_models.py        # 🧱 Pydantic Models for Schema and Structured LLM Output (SQLGenerationTool).
│   ├── gemini_client.py      # 🤖 **NEW:** Wrapper for Gemini API, handling structured output (Tool Call).
│   ├── safe_connector.py     # 🛡️ Database Connector: Enforces READ-ONLY access, Statement Timeout, and Hard Stop Guardrail.
│   ├── hybrid_retriever.py   # 🔍 Hybrid Search (Vector + Keyword) using RRF, enforces Token Budget optimization.
│   ├── llm_agent.py          # 🧠 **Core Logic:** Orchestrates the Agentic Loop, Prompt Builder, and Self-Correction Retry Loop.
│   └── synthesis_module.py   # 📊 Post-processing: PII Scrubbing Layer and final Grounding Constraint application.
├── ingestion/
│   ├── __init__.py
│   ├── introspection.py      # 🗄️ Database Introspection Module: Extracts DDL, especially **Foreign Key (FK) Metadata**.
│   ├── indexing.py           # 🏷️ Schema Indexer: Handles embedding (Vectorization Consistency) and loading into Vector/Keyword stores.
│   └── auxiliary_llm.py      # 💬 (Optional) Module for adding business context to column names.
├── .env                      # File to store sensitive configuration (DB_URI, API Keys).
├── main.py                   # 🚀 Entry point for system initialization, ingestion, and running user queries.
└── README.md                 # Project documentation and setup guide.
```

-----

## 🛠️ Technical Implementation Details

### 1\. Schema Ingestion Pipeline

The robust ingestion process ensures the LLM receives optimal context:

  * **Introspection:** `SQLAlchemy` is used to dynamically connect to the target database and extract table names, column names, data types, and foreign key relationships.
  * **Context Chunking:** Schema information is formatted into semantically descriptive text blocks (e.g., "The `orders` table contains columns for `order_id` and `customer_id`, which links to the `customers` table.").
  * **Vectorization:** These text blocks are embedded using a high-quality model (e.g., `text-embedding-004`) and indexed in the Vector Store.

### 2\. The RAG Agent Workflow

The agent uses a two-stage LLM process for maximum reliability:

1.  **Context Retrieval:** The user's natural language question is used as a query to the Vector Store, retrieving the **Top K** (e.g., K=5) most relevant schema snippets. This drastically limits the context window and reduces noise.
2.  **SQL Generation:**
      * **Prompt Construction:** The core prompt is dynamically injected with System Instructions (defining role and dialect), the Retrieved Schema Context, and the User Question.
      * **LLM Tool Use:** The LLM generates the raw SQL query.
3.  **Validation & Execution:**
      * The generated SQL is parsed and sanitized.
      * The validated query is executed against the database via a **read-only connection**.
4.  **Answer Synthesis:** The raw database result set is passed back to the LLM with the original user query, instructing it to provide a concise, final natural language answer.

### 3\. Prompt Engineering and Reliability

  * **Zero-Shot Instruction:** Explicitly dictated the SQL dialect (e.g., `PostgreSQL`), ensuring the LLM does not default to `SQLite` or another incorrect dialect.
  * **Error Correction Loop (Optional Future Feature):** In the event of a database execution error, the error message can be fed back to the LLM for a revised query generation attempt.
  * **SQL Safety Constraints:** Prompts contain constraints like "Only use `SELECT` statements" and "Do not use `DROP` or `UPDATE`."

-----

## 🚀 Getting Started

### Prerequisites

  * Python 3.9+
  * A target SQL database (PostgreSQL, MySQL, SQLite, etc.)
  * API Key for the chosen LLM (Gemini or OpenAI)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/schemalink.git
cd schemalink

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the root directory:

```env
# Database Connection
DATABASE_URL="postgresql://user:password@host:port/dbname"

# LLM API Key
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
# OR
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
```

### Running the Project

1.  **Ingest Schema:** Run the ingestion script to populate the vector store.
    ```bash
    python scripts/ingest_schema.py
    ```
2.  **Start API:** Launch the FastAPI backend.
    ```bash
    uvicorn app.main:app --reload
    ```
3.  **Interact:** Access the `/docs` endpoint (e.g., `http://127.0.0.1:8000/docs`) to test the agent via the swagger UI.

-----

## 📈 Future Enhancements

  * **Citations:** Integrate a citation mechanism to show the executed SQL query alongside the final answer for transparency and verification.
  * **Multi-Hop Reasoning:** Implement the ability to chain multiple queries to answer highly complex questions (e.g., "Find the top employee in the department with the highest revenue").
  * **Time-Based Context:** Automatically inject the current date into the prompt for questions that involve time-sensitive data (e.g., "What were sales last month?").
