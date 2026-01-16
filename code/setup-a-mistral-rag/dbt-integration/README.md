# dbt + Snowflake Cortex Integration

This folder contains dbt macros and examples for integrating Snowflake Cortex AI capabilities into your dbt workflows.

## Features

- **Auto-generated documentation**: Use Cortex to generate model and column descriptions
- **AI-suggested tests**: Get test recommendations based on data patterns
- **Data quality analysis**: Automated anomaly detection and quality scoring
- **Semantic model enrichment**: Generate business-friendly descriptions

## Setup

### 1. Add to your dbt project

Copy the macros folder to your dbt project:

```bash
cp -r macros/* /path/to/your/dbt/project/macros/
```

### 2. Configure Snowflake connection

Ensure your `profiles.yml` has Cortex-enabled warehouse:

```yaml
your_project:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: your_account
      user: your_user
      password: your_password
      warehouse: CORTEX_ENABLED_WH  # Must have Cortex access
      database: your_database
      schema: your_schema
```

### 3. Enable Cortex in your account

```sql
-- Grant Cortex usage (admin required)
GRANT USAGE ON CORTEX TO ROLE your_role;
```

## Usage

### Auto-generate model descriptions

```yaml
# models/schema.yml
models:
  - name: fct_orders
    description: "{{ cortex_describe_table('fct_orders') }}"
```

### Generate column descriptions

```yaml
columns:
  - name: revenue
    description: "{{ cortex_describe_column('fct_orders', 'revenue') }}"
```

### Get test suggestions

```yaml
columns:
  - name: customer_id
    tests:
      - not_null
      - "{{ cortex_suggest_tests('fct_orders', 'customer_id') }}"
```

### Analyze data quality

```sql
-- In a model or analysis
{{ cortex_data_quality_report('source_table') }}
```

## Macros Reference

| Macro | Purpose |
|-------|---------|
| `cortex_describe_table` | Generate table description |
| `cortex_describe_column` | Generate column description |
| `cortex_suggest_tests` | Suggest dbt tests for a column |
| `cortex_data_quality_report` | Generate data quality analysis |
| `cortex_generate_sql` | Generate SQL from natural language |
| `cortex_explain_model` | Explain what a model does |

## Examples

See the `models/` folder for complete examples of Cortex-enhanced dbt models.
