/*
 * Cortex Description Macros
 *
 * These macros use Snowflake Cortex to auto-generate documentation
 * for your dbt models and columns.
 */

{% macro cortex_describe_table(table_name, schema_name=none, database_name=none) %}
    {#
        Generate a description for a table using Cortex AI.

        Args:
            table_name: Name of the table to describe
            schema_name: Optional schema (defaults to target schema)
            database_name: Optional database (defaults to target database)

        Returns:
            AI-generated table description

        Example:
            description: "{{ cortex_describe_table('fct_orders') }}"
    #}

    {% set schema = schema_name or target.schema %}
    {% set database = database_name or target.database %}
    {% set full_table = database ~ '.' ~ schema ~ '.' ~ table_name %}

    {% set query %}
        WITH table_info AS (
            SELECT
                LISTAGG(column_name || ' (' || data_type || ')', ', ')
                    WITHIN GROUP (ORDER BY ordinal_position) AS columns,
                COUNT(*) AS column_count
            FROM {{ database }}.information_schema.columns
            WHERE table_schema = '{{ schema | upper }}'
              AND table_name = '{{ table_name | upper }}'
        ),
        sample_data AS (
            SELECT *
            FROM {{ full_table }}
            LIMIT 5
        ),
        row_count AS (
            SELECT COUNT(*) AS cnt FROM {{ full_table }}
        )
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Generate a concise business description (2-3 sentences) for this database table. ' ||
            'Focus on what business purpose it serves, not technical details.\n\n' ||
            'Table: {{ table_name }}\n' ||
            'Columns: ' || t.columns || '\n' ||
            'Row count: ' || r.cnt || '\n\n' ||
            'Return only the description, no formatting or prefixes.'
        ) AS description
        FROM table_info t, row_count r
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('Description pending - run dbt to generate') }}
{% endmacro %}


{% macro cortex_describe_column(table_name, column_name, schema_name=none) %}
    {#
        Generate a description for a specific column using Cortex AI.

        Args:
            table_name: Name of the table
            column_name: Name of the column to describe
            schema_name: Optional schema (defaults to target schema)

        Returns:
            AI-generated column description

        Example:
            description: "{{ cortex_describe_column('fct_orders', 'total_amount') }}"
    #}

    {% set schema = schema_name or target.schema %}
    {% set database = target.database %}
    {% set full_table = database ~ '.' ~ schema ~ '.' ~ table_name %}

    {% set query %}
        WITH column_info AS (
            SELECT
                data_type,
                is_nullable,
                column_default
            FROM {{ database }}.information_schema.columns
            WHERE table_schema = '{{ schema | upper }}'
              AND table_name = '{{ table_name | upper }}'
              AND column_name = '{{ column_name | upper }}'
        ),
        column_stats AS (
            SELECT
                COUNT(*) AS total_rows,
                COUNT({{ column_name }}) AS non_null_rows,
                COUNT(DISTINCT {{ column_name }}) AS distinct_values
            FROM {{ full_table }}
        )
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Generate a concise business description (1-2 sentences) for this database column.\n\n' ||
            'Table: {{ table_name }}\n' ||
            'Column: {{ column_name }}\n' ||
            'Data type: ' || c.data_type || '\n' ||
            'Nullable: ' || c.is_nullable || '\n' ||
            'Distinct values: ' || s.distinct_values || ' out of ' || s.total_rows || ' rows\n\n' ||
            'Return only the description, no formatting.'
        ) AS description
        FROM column_info c, column_stats s
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('Description pending') }}
{% endmacro %}


{% macro cortex_describe_model(model_sql) %}
    {#
        Generate a description for a dbt model based on its SQL.

        Args:
            model_sql: The SQL of the model

        Returns:
            AI-generated model description

        Example:
            description: "{{ cortex_describe_model(model.raw_sql) }}"
    #}

    {% set query %}
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Analyze this dbt model SQL and generate a concise business description ' ||
            '(2-3 sentences) explaining what data it produces and its business purpose.\n\n' ||
            'SQL:\n{{ model_sql | replace("'", "''") }}\n\n' ||
            'Return only the description.'
        ) AS description
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('Model description pending') }}
{% endmacro %}
