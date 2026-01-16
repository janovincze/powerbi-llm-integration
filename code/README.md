# PowerBI LLM Stack

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Snowflake](https://img.shields.io/badge/Snowflake-Cortex%20AI-29B5E8)](https://www.snowflake.com/en/data-cloud/cortex/)
[![dbt](https://img.shields.io/badge/dbt-Cloud-FF694B)](https://www.getdbt.com/)
[![PowerBI](https://img.shields.io/badge/PowerBI-F2C811?logo=powerbi)](https://powerbi.microsoft.com/)

Complete implementation code for integrating LLMs with the modern data stack (Snowflake, dbt Cloud, Confluence, PowerBI).

## Key Highlights

| Approach | Accuracy | Best For |
|----------|----------|----------|
| **Self-Hosted Mistral 7B** | **93%+** (domain-tuned) | Full data privacy, predictable costs |
| **Snowflake Cortex AI** | **90%+** | Native integration, zero infrastructure |
| **Claude Opus 4.5** | **95%+** | Complex reasoning, highest accuracy |

> **Claude Opus 4.5 is a game changer** - With extended thinking capabilities and superior reasoning, it achieves 95%+ accuracy on complex SQL/DAX generation tasks, making it the go-to choice when accuracy is paramount.

## Architecture Overview

```
                              ┌─────────────────────────────────────┐
                              │         User Interfaces              │
                              │  ┌─────────┐  ┌─────────┐  ┌──────┐ │
                              │  │ PowerBI │  │Streamlit│  │ Chat │ │
                              │  │ Add-on  │  │  Apps   │  │ API  │ │
                              │  └────┬────┘  └────┬────┘  └───┬──┘ │
                              └───────┼───────────┼───────────┼────┘
                                      │           │           │
                    ┌─────────────────┴───────────┴───────────┴─────────────────┐
                    │                     Hybrid Router                          │
                    │   Routes based on: Data Sensitivity | Query Complexity     │
                    └──────┬─────────────────┬─────────────────┬────────────────┘
                           │                 │                 │
           ┌───────────────┼─────────────────┼─────────────────┼───────────────┐
           │               ▼                 ▼                 ▼               │
           │   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐      │
           │   │   Option A    │   │   Option A+   │   │   Option B    │      │
           │   │  Mistral 7B   │   │   Snowflake   │   │  Claude API   │      │
           │   │  Self-Hosted  │   │   Cortex AI   │   │   + MCP       │      │
           │   │  + RAG        │   │   Native      │   │               │      │
           │   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘      │
           │           │                   │                   │               │
           │           ▼                   ▼                   ▼               │
           │   ┌─────────────────────────────────────────────────────────┐    │
           │   │                    Data Sources                          │    │
           │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │
           │   │  │Snowflake │  │   dbt    │  │Confluence│  │ PowerBI  │ │    │
           │   │  │ Schema   │  │ Metadata │  │   Docs   │  │ Semantic │ │    │
           │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │    │
           │   └─────────────────────────────────────────────────────────┘    │
           └──────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
powerbi-llm-stack/
├── README.md                           # This file
│
├── setup-a-mistral-rag/                # Self-hosted Mistral 7B + RAG
│   ├── docker-compose.yml              # Full stack deployment
│   ├── fine-tuning/
│   │   ├── prepare_dataset.py          # Training data preparation
│   │   ├── train_lora.py               # QLoRA fine-tuning script
│   │   └── requirements.txt
│   ├── rag-pipeline/
│   │   ├── confluence_loader.py        # Confluence document indexer
│   │   ├── snowflake_schema.py         # Schema extraction
│   │   ├── dbt_manifest_parser.py      # dbt metadata parser
│   │   └── vector_store.py             # Qdrant integration
│   ├── inference/
│   │   ├── api_server.py               # vLLM inference API
│   │   ├── iterative_generator.py      # Iterative SQL refinement
│   │   ├── safe_iterative_generator.py # Privacy-aware generation
│   │   └── Dockerfile
│   ├── cortex-examples/                # Snowflake Cortex AI examples
│   │   ├── text_to_sql.sql             # Basic text-to-SQL
│   │   ├── iterative_refinement.sql    # Multi-turn refinement
│   │   ├── dashboard_spec_generator.sql# Dashboard JSON specs
│   │   └── streamlit_generator.sql     # Streamlit app generation
│   ├── streamlit-apps/
│   │   └── sales_dashboard.py          # Example generated dashboard
│   └── dbt-integration/                # dbt + Cortex macros
│       ├── README.md
│       ├── dbt_project.yml
│       ├── macros/
│       │   ├── cortex_describe.sql     # AI-generated descriptions
│       │   ├── cortex_tests.sql        # AI-suggested tests
│       │   ├── cortex_data_quality.sql # Data quality reports
│       │   └── cortex_generate.sql     # SQL/model generation
│       ├── models/
│       │   ├── schema.yml
│       │   ├── staging/stg_customers.sql
│       │   └── marts/
│       │       ├── fct_orders.sql
│       │       └── mart_daily_sales.sql
│       └── analyses/
│           └── cortex_analysis_examples.sql
│
├── setup-b-claude-mcp/                 # Claude API + MCP servers
│   ├── mcp-servers/
│   │   ├── snowflake-mcp/              # Snowflake MCP server
│   │   ├── dbt-mcp/                    # dbt metadata MCP
│   │   └── config.json                 # MCP registry
│   ├── claude-integration/
│   │   ├── client.py                   # Claude API wrapper
│   │   └── prompts/                    # System prompts
│   └── examples/
│       ├── chat_with_data.py
│       ├── generate_dashboard.py
│       └── iterative_refinement.py     # Multi-turn generation
│
├── powerbi-templates/                  # PowerBI standards
│   ├── themes/
│   │   └── company-theme.json          # Visual formatting
│   ├── dax-templates/
│   │   ├── time-intelligence.dax       # YoY, MTD, QTD
│   │   └── common-measures.dax         # Standard calculations
│   ├── report-templates/
│   │   └── standard-layout.pbit        # Template file
│   └── prompts/                        # LLM prompt templates
│       ├── README.md
│       ├── dax_generation.yaml
│       ├── sql_generation.yaml
│       ├── dashboard_design.yaml
│       ├── data_analysis.yaml
│       ├── report_narrative.yaml
│       └── troubleshooting.yaml
│
├── ba-copilot-addon/                   # PowerBI custom visual
│   ├── frontend/                       # TypeScript/React visual
│   │   ├── src/
│   │   │   ├── visual.ts
│   │   │   ├── components/
│   │   │   └── services/
│   │   ├── pbiviz.json
│   │   └── package.json
│   └── backend/                        # FastAPI backend
│       ├── app/
│       │   ├── main.py
│       │   ├── routers/
│       │   └── services/
│       │       ├── claude_client.py
│       │       ├── rag_pipeline.py
│       │       ├── hybrid_router.py    # Smart routing
│       │       └── metrics.py          # Usage tracking
│       ├── Dockerfile
│       └── requirements.txt
│
└── dashboard-automation/               # NL to dashboard
    ├── nl2dashboard/
    │   ├── spec_generator.py
    │   ├── dax_generator.py
    │   └── pbi_deployer.py
    └── examples/
        └── sales_dashboard.json
```

## Quick Start

### Option A: Self-Hosted Mistral + RAG

**Infrastructure Requirements:**
- **Development**: MacBook M1/M2/M3 (runs locally, $0 hardware cost)
- **Small team**: 1x RTX 4090 or cloud GPU ($3k-5k)
- **Production**: A100 40GB or 2x RTX 4090 ($15k+)

> **The real cost is expertise, not hardware.** A single ML engineer can maintain this stack, and we provide comprehensive guides to get started.

```bash
cd setup-a-mistral-rag

# Set environment variables
export HF_TOKEN=your_huggingface_token
export CONFLUENCE_URL=https://your-company.atlassian.net/wiki
export CONFLUENCE_USER=your-email
export CONFLUENCE_API_KEY=your-api-key

# For local development (MacBook)
pip install -r fine-tuning/requirements.txt
python fine-tuning/train_lora.py --model mistralai/Mistral-7B-Instruct-v0.3 \
    --output_dir ./models/sql-lora \
    --use_mps  # Apple Silicon acceleration

# For production (GPU server)
docker-compose up -d
```

### Option A+: Snowflake Cortex AI (Zero Infrastructure)

```sql
-- No setup required! Just use Cortex functions in Snowflake
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'mistral-large2',
    'Generate SQL to find top 10 customers by revenue'
);

-- Or use Cortex Analyst for semantic layer queries
-- See cortex-examples/ for comprehensive examples
```

### Option B: Claude + MCP

```bash
cd setup-b-claude-mcp

# Set environment variables
export ANTHROPIC_API_KEY=your_anthropic_key
export SNOWFLAKE_ACCOUNT=your_account
export SNOWFLAKE_USER=your_user
export SNOWFLAKE_PASSWORD=your_password

# Install and run
pip install -r requirements.txt
python claude-integration/client.py
```

### BA Copilot Add-on

```bash
# Backend
cd ba-copilot-addon/backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (PowerBI Visual)
cd ba-copilot-addon/frontend
npm install
pbiviz package
# Output: dist/BACopilot.pbiviz
```

## Data Privacy & Security

### Configurable Exposure Levels

The system supports three data exposure levels for iterative refinement:

| Level | What LLM Sees | Use Case |
|-------|---------------|----------|
| `schema_only` | Table/column names only | External APIs, compliance |
| `aggregated` | Summary statistics | General queries |
| `full` | Actual data samples | Self-hosted only |

```python
from inference.safe_iterative_generator import SafeIterativeGenerator, ExposureLevel

generator = SafeIterativeGenerator(
    exposure_level=ExposureLevel.SCHEMA_ONLY  # Safe for external APIs
)
```

### Hybrid Routing

The `HybridRouter` automatically routes queries based on sensitivity:

```python
from services.hybrid_router import HybridRouter

router = HybridRouter()
result = router.route_query(
    query="Show me customer PII with payment details",
    context={"tables": ["customers", "payments"]}
)
# Routes to: self-hosted Mistral (sensitive data detected)
```

## dbt + Cortex Integration

Use Snowflake Cortex AI directly in your dbt models:

```sql
-- Auto-generate column descriptions
{{ cortex_describe('stg_customers', 'customer_segment') }}

-- Generate data quality reports
{{ cortex_data_quality('fct_orders') }}

-- AI-suggested tests
{{ cortex_suggest_tests('dim_products') }}
```

See `setup-a-mistral-rag/dbt-integration/` for complete examples.

## Prompt Templates

Standardized YAML prompt templates for consistent LLM outputs:

```yaml
# powerbi-templates/prompts/dax_generation.yaml
name: dax_generation
system_prompt: |
  You are a DAX expert for {company_name}.
  Follow these patterns: {dax_patterns}
  ...

variables:
  company_name: "Your Company"
  dax_patterns: "..."
```

Available templates:
- `dax_generation.yaml` - DAX measure generation
- `sql_generation.yaml` - SQL query generation
- `dashboard_design.yaml` - Dashboard layout design
- `data_analysis.yaml` - Data analysis framework
- `report_narrative.yaml` - Executive summaries
- `troubleshooting.yaml` - DAX/SQL debugging

## Environment Variables

Create a `.env` file:

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Snowflake
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your_database

# Confluence (for RAG)
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USER=your-email@company.com
CONFLUENCE_API_KEY=your_api_key

# Qdrant (for self-hosted RAG)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Hugging Face (for self-hosted models)
HF_TOKEN=hf_...
```

## Comparison Matrix

| Criteria | Mistral + RAG | Cortex AI | Claude + MCP |
|----------|---------------|-----------|--------------|
| **Accuracy** | 93%+ (tuned) | 90%+ | 95%+ |
| **Setup Cost** | $0-15k | $0 | $0 |
| **Running Cost** | Fixed | Per-credit | Per-token |
| **Data Privacy** | Full control | In Snowflake | API-based |
| **Setup Time** | Days-weeks | Minutes | Hours |
| **Best For** | Compliance, high volume | Existing Snowflake users | Complex reasoning |

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Related Article

This repository accompanies the article: **"LLM Integration with the Modern Data Stack: Snowflake, dbt Cloud, Confluence, and PowerBI"**

See `../article.md` for the full guide.

---

**Maintained by:** [@janovincze](https://github.com/janovincze)
