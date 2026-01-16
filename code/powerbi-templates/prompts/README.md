# LLM Prompt Templates for PowerBI

This folder contains reusable prompt templates for LLM-assisted PowerBI development. These templates ensure consistent, high-quality outputs aligned with company standards.

## Template Types

| Template | Purpose |
|----------|---------|
| `dax_generation.yaml` | Generate DAX measures from natural language |
| `sql_generation.yaml` | Generate SQL queries for PowerBI datasets |
| `dashboard_design.yaml` | Design dashboard layouts and visual specifications |
| `data_analysis.yaml` | Analyze data and generate insights |
| `report_narrative.yaml` | Generate report summaries and narratives |
| `troubleshooting.yaml` | Debug DAX/SQL issues |

## Usage

### Python Example

```python
import yaml
from anthropic import Anthropic

# Load template
with open('prompts/dax_generation.yaml', 'r') as f:
    template = yaml.safe_load(f)

# Build prompt
system_prompt = template['system_prompt'].format(
    company_name="Acme Corp",
    primary_color="#0066CC",
    secondary_color="#00994D"
)

# Call LLM
client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system=system_prompt,
    messages=[{"role": "user", "content": "Create a YoY growth measure for revenue"}]
)
```

### Variables

Templates use `{variable_name}` syntax for customization:

- `{company_name}` - Your company name
- `{primary_color}` - Primary brand color (hex)
- `{secondary_color}` - Secondary brand color (hex)
- `{schema}` - Database schema description
- `{glossary}` - Business term definitions
- `{dax_patterns}` - Standard DAX patterns to follow

## Customization

1. Copy the template you want to customize
2. Modify the system prompt and examples
3. Add company-specific terminology to the glossary section
4. Test with sample queries before production use

## Best Practices

- Always include schema context for SQL/DAX generation
- Provide examples of desired output format
- Include business glossary for domain-specific terms
- Specify error handling expectations
- Request explanations for complex logic
