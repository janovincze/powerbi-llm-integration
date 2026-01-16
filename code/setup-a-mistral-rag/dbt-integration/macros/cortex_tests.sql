/*
 * Cortex Test Suggestion Macros
 *
 * These macros use Snowflake Cortex to analyze data patterns
 * and suggest appropriate dbt tests.
 */

{% macro cortex_suggest_tests(table_name, column_name, schema_name=none) %}
    {#
        Analyze a column and suggest appropriate dbt tests.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            schema_name: Optional schema name

        Returns:
            List of suggested test names

        Example:
            tests:
              - not_null
              {{ cortex_suggest_tests('fct_orders', 'customer_id') }}
    #}

    {% set schema = schema_name or target.schema %}
    {% set database = target.database %}
    {% set full_table = database ~ '.' ~ schema ~ '.' ~ table_name %}

    {% set query %}
        WITH column_analysis AS (
            SELECT
                '{{ column_name }}' AS column_name,
                COUNT(*) AS total_rows,
                COUNT({{ column_name }}) AS non_null_count,
                COUNT(DISTINCT {{ column_name }}) AS distinct_count,
                MIN({{ column_name }})::VARCHAR AS min_value,
                MAX({{ column_name }})::VARCHAR AS max_value
            FROM {{ full_table }}
        ),
        column_meta AS (
            SELECT data_type, is_nullable
            FROM {{ database }}.information_schema.columns
            WHERE table_schema = '{{ schema | upper }}'
              AND table_name = '{{ table_name | upper }}'
              AND column_name = '{{ column_name | upper }}'
        )
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Based on this column analysis, suggest appropriate dbt tests.\n\n' ||
            'Column: {{ column_name }}\n' ||
            'Data type: ' || m.data_type || '\n' ||
            'Total rows: ' || a.total_rows || '\n' ||
            'Non-null count: ' || a.non_null_count || '\n' ||
            'Distinct count: ' || a.distinct_count || '\n' ||
            'Min value: ' || a.min_value || '\n' ||
            'Max value: ' || a.max_value || '\n\n' ||
            'Available dbt tests: not_null, unique, accepted_values, relationships\n\n' ||
            'Return ONLY a YAML list of test names, like:\n' ||
            '- not_null\n' ||
            '- unique\n\n' ||
            'No explanation, just the list.'
        ) AS suggestions
        FROM column_analysis a, column_meta m
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('# Tests pending analysis') }}
{% endmacro %}


{% macro cortex_analyze_test_coverage(model_name) %}
    {#
        Analyze a model and identify columns that may need tests.

        Args:
            model_name: Name of the dbt model

        Returns:
            Analysis of test coverage gaps
    #}

    {% set schema = target.schema %}
    {% set database = target.database %}

    {% set query %}
        WITH columns AS (
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM {{ database }}.information_schema.columns
            WHERE table_schema = '{{ schema | upper }}'
              AND table_name = '{{ model_name | upper }}'
        )
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Analyze these columns and identify which ones likely need dbt tests.\n\n' ||
            'Columns:\n' ||
            (SELECT LISTAGG(column_name || ' (' || data_type || ', nullable=' || is_nullable || ')', '\n')
             FROM columns) ||
            '\n\nFor each column that needs tests, explain why and what tests.\n' ||
            'Focus on: primary keys, foreign keys, business-critical fields, date fields.\n' ||
            'Format as a checklist.'
        ) AS analysis
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('Analysis pending') }}
{% endmacro %}


{% macro cortex_validate_relationships(source_table, source_column, target_table, target_column) %}
    {#
        Validate a foreign key relationship and identify orphaned records.

        Args:
            source_table: Table containing the foreign key
            source_column: Foreign key column
            target_table: Referenced table
            target_column: Primary key column in target

        Returns:
            Validation report with any issues found
    #}

    {% set schema = target.schema %}
    {% set database = target.database %}

    {% set query %}
        WITH orphaned AS (
            SELECT COUNT(*) AS orphan_count
            FROM {{ database }}.{{ schema }}.{{ source_table }} s
            LEFT JOIN {{ database }}.{{ schema }}.{{ target_table }} t
                ON s.{{ source_column }} = t.{{ target_column }}
            WHERE s.{{ source_column }} IS NOT NULL
              AND t.{{ target_column }} IS NULL
        ),
        total AS (
            SELECT COUNT(*) AS total_count
            FROM {{ database }}.{{ schema }}.{{ source_table }}
            WHERE {{ source_column }} IS NOT NULL
        )
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Analyze this foreign key relationship:\n\n' ||
            'Source: {{ source_table }}.{{ source_column }}\n' ||
            'Target: {{ target_table }}.{{ target_column }}\n' ||
            'Orphaned records: ' || o.orphan_count || '\n' ||
            'Total records with FK: ' || t.total_count || '\n\n' ||
            'Provide a brief assessment: Is this relationship valid? Any concerns?\n' ||
            'If orphans exist, suggest possible causes and remediation.'
        ) AS validation
        FROM orphaned o, total t
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('Validation pending') }}
{% endmacro %}
