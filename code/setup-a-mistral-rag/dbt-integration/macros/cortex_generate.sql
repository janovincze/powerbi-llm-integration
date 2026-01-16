/*
 * Cortex SQL Generation Macros
 *
 * These macros use Snowflake Cortex to generate SQL and dbt models
 * from natural language descriptions.
 */

{% macro cortex_generate_sql(description, tables=none) %}
    {#
        Generate SQL from a natural language description.

        Args:
            description: Natural language description of desired query
            tables: Optional list of table names to use

        Returns:
            Generated SQL query

        Example:
            {{ cortex_generate_sql('Find customers who ordered more than 5 times last month') }}
    #}

    {% set schema = target.schema %}
    {% set database = target.database %}

    {% set schema_context = '' %}
    {% if tables %}
        {% for table in tables %}
            {% set cols_query %}
                SELECT LISTAGG(column_name || ' ' || data_type, ', ')
                FROM {{ database }}.information_schema.columns
                WHERE table_schema = '{{ schema | upper }}'
                  AND table_name = '{{ table | upper }}'
            {% endset %}
            {% set cols = run_query(cols_query) %}
            {% set schema_context = schema_context ~ table ~ '(' ~ cols.rows[0][0] ~ ')\n' %}
        {% endfor %}
    {% endif %}

    {% set query %}
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Generate a Snowflake SQL query for this request:\n\n' ||
            {% if schema_context %}
            'Available tables:\n{{ schema_context }}\n\n' ||
            {% endif %}
            'Request: {{ description }}\n\n' ||
            'Requirements:\n' ||
            '- Use Snowflake SQL syntax\n' ||
            '- Include comments explaining the logic\n' ||
            '- Use CTEs for complex queries\n' ||
            '- Return only the SQL, no explanation\n\n' ||
            'SQL:'
        ) AS generated_sql
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('-- SQL generation pending') }}
{% endmacro %}


{% macro cortex_generate_model(model_name, description, source_tables) %}
    {#
        Generate a complete dbt model from description.

        Args:
            model_name: Name for the new model
            description: What the model should do
            source_tables: List of source table names

        Returns:
            Complete dbt model SQL with config and documentation

        Example:
            {{ cortex_generate_model(
                'fct_daily_sales',
                'Daily sales aggregation by product and region',
                ['raw_orders', 'raw_products']
            ) }}
    #}

    {% set schema = target.schema %}
    {% set database = target.database %}

    -- Gather schema info for source tables
    {% set schema_info = [] %}
    {% for table in source_tables %}
        {% set cols_query %}
            SELECT column_name, data_type
            FROM {{ database }}.information_schema.columns
            WHERE table_schema = '{{ schema | upper }}'
              AND table_name = '{{ table | upper }}'
            ORDER BY ordinal_position
        {% endset %}
        {% set cols = run_query(cols_query) %}
        {% do schema_info.append({'table': table, 'columns': cols}) %}
    {% endfor %}

    {% set query %}
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Generate a complete dbt model with the following specifications:\n\n' ||
            'Model name: {{ model_name }}\n' ||
            'Description: {{ description }}\n\n' ||
            'Source tables:\n' ||
            {% for info in schema_info %}
            '{{ info.table }}:\n' ||
            {% for row in info.columns.rows %}
            '  - {{ row[0] }} ({{ row[1] }})\n' ||
            {% endfor %}
            {% endfor %}
            '\n\nRequirements:\n' ||
            '1. Start with dbt config block (materialized, tags)\n' ||
            '2. Add model documentation as a comment\n' ||
            '3. Use ref() or source() for table references\n' ||
            '4. Use CTEs for clarity\n' ||
            '5. Include appropriate column aliases\n' ||
            '6. Add inline comments for complex logic\n\n' ||
            'Return the complete model SQL:'
        ) AS model_sql
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('-- Model generation pending') }}
{% endmacro %}


{% macro cortex_optimize_query(sql_query) %}
    {#
        Analyze and optimize an existing SQL query.

        Args:
            sql_query: The SQL to optimize

        Returns:
            Optimized SQL with explanation
    #}

    {% set query %}
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Optimize this Snowflake SQL query for better performance:\n\n' ||
            '```sql\n{{ sql_query | replace("'", "''") }}\n```\n\n' ||
            'Consider:\n' ||
            '1. Query structure and join order\n' ||
            '2. Predicate pushdown opportunities\n' ||
            '3. Unnecessary columns in SELECT\n' ||
            '4. Subquery vs CTE vs temp table\n' ||
            '5. Clustering key alignment\n\n' ||
            'Return:\n' ||
            '1. Optimized SQL\n' ||
            '2. Brief explanation of changes'
        ) AS optimization
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('-- Optimization pending') }}
{% endmacro %}


{% macro cortex_generate_incremental_logic(model_name, primary_key, timestamp_column) %}
    {#
        Generate incremental model logic for an existing model.

        Args:
            model_name: Name of the model to make incremental
            primary_key: Primary key column(s)
            timestamp_column: Column to use for incremental filtering

        Returns:
            Incremental model template
    #}

    {% set query %}
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Generate dbt incremental model logic for:\n\n' ||
            'Model: {{ model_name }}\n' ||
            'Primary key: {{ primary_key }}\n' ||
            'Timestamp column: {{ timestamp_column }}\n\n' ||
            'Include:\n' ||
            '1. Config block with incremental strategy (merge)\n' ||
            '2. is_incremental() macro usage\n' ||
            '3. Proper unique_key handling\n' ||
            '4. Lookback window for late-arriving data\n\n' ||
            'Return a complete incremental model template.'
        ) AS incremental_logic
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('-- Incremental logic pending') }}
{% endmacro %}
