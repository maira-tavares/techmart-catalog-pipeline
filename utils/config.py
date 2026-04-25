# utils/config.py
# Central configuration for the TechMart Catalog Intelligence Pipeline.

from pathlib import Path
import subprocess
from datetime import datetime

#############################################################################################
#  Base paths 
#############################################################################################
REPO_ROOT   = Path("/Workspace/Repos/ts.maira@gmail.com/techmart-catalog-pipeline")
PROMPTS_DIR = REPO_ROOT / "prompts"
UTILS_DIR   = REPO_ROOT / "utils"

#############################################################################################
#  Prompt template files
#############################################################################################
PROMPT_EXTRACTION = "prompt_extraction.j2"
PROMPT_JUDGE      = "prompt_judge.j2"
# Version is tied to the Git commit — any change to a prompt file and subsequent commit automatically produces a new traceable version
try:
    git_hash = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(REPO_ROOT)
    ).decode("utf-8").strip()
    PROMPT_VERSION = f"v2.0-{git_hash}"
except Exception:
    PROMPT_VERSION = "v2.0-unknown"

#############################################################################################
#  Delta table names
#############################################################################################
BRONZE_PRODUCTS   = "main.bronze_techmart.raw_products"
BRONZE_VENDORS    = "main.bronze_techmart.raw_vendors"
SILVER_PRODUCTS   = "main.silver_techmart.products"
SILVER_VENDORS    = "main.silver_techmart.vendors"
LLM_EXTRACTED     = "main.silver_techmart.llm_extracted"
SILVER_TAXONOMY   = "main.silver_techmart.taxonomy"
TAXONOMY_ENRICHED = "main.silver_techmart.taxonomy_enriched"
GOLD_SUMMARY      = "main.gold_techmart.product_summary"

#############################################################################################
#  LLM configuration 
#############################################################################################
LLM_PROVIDER = "groq"
LLM_MODEL    = "llama-3.1-8b-instant"
LLM_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
LLM_API_KEY  = dbutils.secrets.get(scope="techmart", key="groq-api-key")


#############################################################################################
#  Allowed values (taxonomy)
#############################################################################################
ALLOWED_SUBCATEGORIES = [
    "Televisions", "Computers", "Accessories", "Phones", "Smartwatches"
]

APPROVED_TAXONOMY = [
    "Televisions", "Computers", "Accessories", "Phones", "Smartwatches",
    "Printers", "Cameras", "Consoles", "Hardware"
]
#############################################################################################
#  MLflow 
#############################################################################################
MLFLOW_EXPERIMENT = "/Users/ts.maira@gmail.com/techmart-llm-extraction"


#############################################################################################
print(f"✅ Config loaded")
print(f"Prompt version : {PROMPT_VERSION}")
print(f"LLM model      : {LLM_MODEL}")
print(f"Provider       : {LLM_PROVIDER}")