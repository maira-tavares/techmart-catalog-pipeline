# TechMart Catalog Intelligence Pipeline

A production-grade data engineering pipeline built on Databricks that ingests raw electronics vendor data, applies data quality and normalization, enriches product descriptions using LLM extraction, validates results with an LLM-as-Judge pattern, and surfaces a clean analytical Gold table.

---

## Business Context

TechMart is a consumer electronics retailer that receives product catalog data from multiple vendors in raw Excel format. Each vendor describes their products inconsistently — mixed units, unstructured descriptions, duplicate vendor names. This pipeline standardizes, enriches, and validates that data automatically, making it analytics-ready.

---

## Architecture

```
electronics_dataset.xlsx
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  BRONZE — Raw ingestion                              │
│  techmart_bronze.raw_products                        │
│  techmart_bronze.raw_vendors                         │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  SILVER — Cleaned and normalized                     │
│  techmart_silver.products    (weight→kg, price→USD)  │
│  techmart_silver.vendors     (deduped, normalized)   │
│  techmart_silver.llm_extracted  (LLM extraction)     │
│  techmart_silver.taxonomy    (LLM Judge results)     │
│  techmart_silver.taxonomy_enriched (vendor join)     │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  GOLD — Business-ready analytics                     │
│  techmart_gold.product_summary                       │
│  Category, Sub-Category, #Products, AVG/Min/Max Price│
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Platform | Databricks Free Edition | Unified analytics platform with native Delta Lake support |
| Storage | Delta Lake | ACID transactions, schema evolution, time travel |
| Orchestration | Databricks Notebooks + dbutils | Native integration, no extra tooling needed |
| LLM Provider | Groq (llama-3.1-8b-instant) | Generous free tier, OpenAI-compatible API, fast inference |
| Prompt Templating | Jinja2 | Industry standard, separates prompt logic from content |
| LLM Output Validation | Pydantic | Type-safe validation with automatic retry on invalid output |
| Experiment Tracking | MLflow | Native Databricks integration, logs prompts, tokens, latency |
| Version Control | GitHub + Databricks Repos | Full Git integration with automatic sync |
| CI/CD | GitHub Actions | Automatic unit test execution on every push |
| Secrets Management | Databricks Secrets Manager | API keys never exposed in code or version control |

---

## Project Structure

```
techmart-catalog-pipeline/
│
├── pipeline/                        # Production pipeline notebooks
│   ├── 00_run_pipeline              # Master orchestrator — runs all stages
│   ├── 01_bronze_ingest             # Stage 1: Raw Excel ingestion
│   ├── 02_silver_standardize        # Stage 2: Normalization and cleaning
│   ├── 03_llm_extraction            # Stage 3: LLM-based field extraction
│   ├── 04_llm_judge                 # Stage 4: LLM-as-Judge validation
│   ├── 05_silver_taxonomy           # Stage 5: Taxonomy enrichment
│   └── 06_gold_aggregation          # Stage 6: Business aggregation
│
├── setup_pipeline/                  # One-time setup scripts
│   ├── idempotency_check         # Validates pipeline idempotency
│   ├── data_quality              # Applies Delta constraints
│   └── schema_evolution_demo     # Demonstrates schema evolution
│
├── utils/                           # Shared utilities
│   ├── __init__.py 
│   ├── config.py                    # Centralized configuration and secrets
│   ├── llm_utils.py                 # Generic LLM call with retry logic
│   └── states.py                    # Pydantic models for LLM output validation
│
├── prompts/                         # Versioned prompt templates
│   ├── prompt_extraction.j2         # Jinja2 extraction prompt
│   └── prompt_judge.j2              # Jinja2 judge prompt
│
├── tests/                           # Unit tests
│   ├── test_transformations.py      # 37 tests for Silver transformations
│   └── test_runner                  # Databricks notebook test runner
│
├── .github/
│   └── workflows/
│       └── ci.yml                   # GitHub Actions CI pipeline
│
└── README.md
```

---

## Pipeline Stages

### Stage 1 — Bronze Ingestion
Reads two raw Excel files from a Unity Catalog Volume and writes them as Delta tables preserving data exactly as received. All columns are stored as strings — no transformations at this layer.

| File | Table |
|------|-------|
| `electronics_dataset_products.xlsx` | `techmart_bronze.raw_products` |
| `electronics_dataset_vendors.xlsx` | `techmart_bronze.raw_vendors` |

### Stage 2 — Silver Standardization
Applies cleaning and normalization to both Bronze tables independently.

**Products** (`raw_products` → `techmart_silver.products`):
- Weight normalized to kg float — handles 15+ formats
- Price normalized to USD float — handles 10+ formats
- Product description lowercased and cleaned for LLM input

**Vendors** (`raw_vendors` → `techmart_silver.vendors`):
- Legal suffixes removed (Inc, Ltd, Co, Corp)
- Extra spaces collapsed
- Known brand variations mapped to canonical names

### Stage 3 — LLM Extraction
Calls the Groq API (llama-3.1-8b-instant) to extract `name`, `brand`, and `sub_category` from each product description. 
| Source | Target |
|--------|--------|
| `techmart_silver.products` | `techmart_silver.llm_extracted` |

Features:
- Jinja2 prompt templates with system/user role separation
- Pydantic validation of LLM output with automatic retry on invalid response
- Exponential backoff retry logic for rate limit and network errors
- MLflow tracing: logs prompt template, model, tokens, latency, success rate

### Stage 4 — LLM Judge
A second LLM call validates the extraction against the approved taxonomy. The Judge independently classifies each product and compares with the extractor's result. 

| Source | Target |
|--------|--------|
| `techmart_silver.llm_extracted` | `techmart_silver.taxonomy` |

Features:
- `judge_taxonomy`: Judge's own classification
- `judge_approved`: True if Judge agrees with extractor
- `judge_reason`: Explanation when disagreement occurs
- MLflow tracing: logs approval rate, token usage, latency

### Stage 5 — Silver Taxonomy Enrichment
Joins Judge results with vendor information and maps sub-categories to parent categories. Produces the final enriched Silver table ready for Gold aggregation.

| Sources | Target |
|---------|--------|
| `techmart_silver.taxonomy` + `techmart_silver.vendors` + `techmart_silver.products` | `techmart_silver.taxonomy_enriched` |


### Stage 6 — Gold Aggregation
Aggregates only Judge-approved records by Category and Sub-Category, producing business-ready metrics: number of products, average price, minimum price, maximum price.
| Source | Target |
|--------|--------|
| `techmart_silver.taxonomy_enriched` | `techmart_gold.product_summary` |

| Metric | Description |
|--------|-------------|
| `num_products` | Number of products per category |
| `avg_price_usd` | Average unit price |
| `min_price_usd` | Lowest unit price |
| `max_price_usd` | Highest unit price |
---

## Setup Instructions

### Prerequisites
- Databricks Free Edition workspace
- GitHub account
- Groq API key (free at console.groq.com)

### 1 — Clone the Repository
In Databricks: Workspace → Repos → Add Repo → paste the GitHub URL.

### 2 — Upload Source Data
Go to: Catalog → main → techmart_bronze → raw_files → Upload to this volume

Upload both files:
- `electronics_dataset_products.xlsx`
- `electronics_dataset_vendors.xlsx`

### 3 — Configure Secrets
Install the Databricks CLI locally and run:

```bash
databricks configure --token
databricks secrets create-scope --scope techmart
databricks secrets put --scope techmart --key groq-api-key --string-value "your-key-here"
```

### 4 — Run Setup Scripts
Run these notebooks once in order:
1. `setup_pipeline/data_quality` — applies Delta constraints
2. `setup_pipeline/schema_evolution_demo` — optional demo

### 5 — Run the Pipeline
Open `pipeline/00_run_pipeline` and click **Run All**.

Expected output:
```
Bronze — raw_products          30 rows
Bronze — raw_vendors           30 rows
Silver — products              30 rows
Silver — vendors               30 rows
Silver — llm_extracted         30 rows
Silver — taxonomy              30 rows
Silver — taxonomy_enriched     30 rows
Gold   — product_summary        5 rows
```

---

## Data Quality

Delta constraints are applied at Bronze and Silver layers:

| Layer | Table | Constraint |
|-------|-------|------------|
| Bronze | raw_products | product_id NOT NULL, description NOT EMPTY |
| Bronze | raw_vendors | product_id NOT NULL, vendor_name NOT EMPTY |
| Silver | products | weight_kg > 0, unit_price_usd > 0 |
| Silver | vendors | vendor_name NOT NULL AND NOT EMPTY |
| Gold | product_summary | category NOT NULL, num_products > 0 |

---

## MLflow Traceability

Every LLM run logs to the `techmart-llm-extraction` MLflow experiment:

| What is logged | Type | Example |
|---------------|------|---------|
| Prompt template | Artifact | `prompt_extraction.j2` |
| Prompt version | Parameter | `v1` |
| Model | Parameter | `llama-3.1-8b-instant` |
| Provider | Parameter | `groq` |
| Total input tokens | Metric | `3420` |
| Total output tokens | Metric | `287` |
| Average latency | Metric | `0.823s` |
| Success rate | Metric | `1.0` |
| Approval rate | Metric | `0.8` |

---

## CI/CD

GitHub Actions runs automatically on every push to main:

```
Push to GitHub
      ↓
Install Python 3.11 + pytest
      ↓
Run 37 unit tests
      ↓
✅ All passed → green commit
❌ Any failed → red commit + email notification
```

---

## Idempotency

The pipeline is safe to run multiple times. All writes use `.mode("overwrite")` with `overwriteSchema=True` ensuring that re-running produces identical row counts and data. Verified by `setup_pipeline/idempotency_check`.

---

## Author

Maira Tavares
Data Engineer
[github.com/maira-tavares](https://github.com/maira-tavares)