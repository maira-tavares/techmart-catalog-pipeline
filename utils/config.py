# utils/config.py
# Central configuration for the TechMart Catalog Intelligence Pipeline.
from pathlib import Path
import subprocess

# ══════════════════════════════════════════════════════════════════════════════
# STORAGE — Schema and table names
# Convention: project_layer groups all schemas alphabetically in Catalog
# ══════════════════════════════════════════════════════════════════════════════
BRONZE_SCHEMA = "techmart_bronze"
SILVER_SCHEMA = "techmart_silver"
GOLD_SCHEMA   = "techmart_gold"

# Volume paths — raw source files landing zone
PRODUCTS_FILE = f"/Volumes/main/{BRONZE_SCHEMA}/raw_files/electronics_dataset_products.xlsx"
VENDORS_FILE  = f"/Volumes/main/{BRONZE_SCHEMA}/raw_files/electronics_dataset_vendors.xlsx"

# Delta table full names: catalog.schema.table
BRONZE_PRODUCTS   = f"main.{BRONZE_SCHEMA}.raw_products"
BRONZE_VENDORS    = f"main.{BRONZE_SCHEMA}.raw_vendors"
SILVER_PRODUCTS   = f"main.{SILVER_SCHEMA}.products"
SILVER_VENDORS    = f"main.{SILVER_SCHEMA}.vendors"
LLM_EXTRACTED     = f"main.{SILVER_SCHEMA}.llm_extracted"
SILVER_TAXONOMY   = f"main.{SILVER_SCHEMA}.taxonomy"
TAXONOMY_ENRICHED = f"main.{SILVER_SCHEMA}.taxonomy_enriched"
GOLD_SUMMARY      = f"main.{GOLD_SCHEMA}.product_summary"


# ══════════════════════════════════════════════════════════════════════════════
# LLM — Model and API configuration
# ══════════════════════════════════════════════════════════════════════════════

LLM_PROVIDER = "groq"
LLM_MODEL    = "llama-3.1-8b-instant"# "llama-3.3-70b-versatile"
LLM_API_URL  = "https://api.groq.com/openai/v1/chat/completions"

LLM_MAX_RETRIES = 5
LLM_RETRY_DELAY = 20.0
LLM_TIMEOUT     = 60

def get_api_key(dbutils) -> str:
    """
    Retrieves the Groq API key from Databricks Secrets Manager.
    API keys are never hardcoded — always retrieved at runtime via Secrets.

    Args:
        dbutils: Databricks dbutils object — passed from the calling notebook.

    Returns:
        Groq API key string.
    """
    return dbutils.secrets.get(scope="techmart", key="groq-api-key")

# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS — Template filenames and taxonomy values
# ══════════════════════════════════════════════════════════════════════════════
PROMPT_FOLDER = "prompts"
PROMPT_EXTRACTION = "prompt_extraction.j2"
PROMPT_JUDGE      = "prompt_judge.j2"
PROMPT_VERSION = "v1"

# Allowed sub-categories passed to the LLM extraction prompt
ALLOWED_SUBCATEGORIES = [
    "Televisions", "Computers", "Accessories", "Phones", "Smartwatches"
]

# Approved taxonomy used by the LLM Judge for validation
APPROVED_TAXONOMY = [
    "Televisions", "Computers", "Accessories", "Phones", "Smartwatches",
    "Printers", "Cameras", "Consoles", "Hardware"
]
    
# ══════════════════════════════════════════════════════════════════════════════
# MLFLOW — Experiment tracking
# ══════════════════════════════════════════════════════════════════════════════
MLFLOW_EXPERIMENT_NAME = "techmart-llm-extraction"


# ══════════════════════════════════════════════════════════════════════════════
print(f"✅ Config loaded")