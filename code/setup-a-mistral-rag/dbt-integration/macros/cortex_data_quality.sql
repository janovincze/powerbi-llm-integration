/*
 * Cortex Data Quality Macros
 *
 * These macros use Snowflake Cortex to analyze data quality
 * and generate insights about your data.
 */

{% macro cortex_data_quality_report(table_name, schema_name=none) %}
    {#
        Generate a comprehensive data quality report for a table.

        Args:
            table_name: Name of the table to analyze
            schema_name: Optional schema name

        Returns:
            SQL that generates a data quality report
    #}

    {% set schema = schema_name or target.schema %}
    {% set database = target.database %}
    {% set full_table = database ~ '.' ~ schema ~ '.' ~ table_name %}

    WITH column_stats AS (
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM {{ database }}.information_schema.columns
        WHERE table_schema = '{{ schema | upper }}'
          AND table_name = '{{ table_name | upper }}'
    ),
    quality_metrics AS (
        SELECT
            '{{ table_name }}' AS table_name,
            COUNT(*) AS total_rows,
            {% for col in get_columns_in_relation(ref(table_name)) %}
            SUM(CASE WHEN {{ col.name }} IS NULL THEN 1 ELSE 0 END) AS {{ col.name }}_nulls,
            COUNT(DISTINCT {{ col.name }}) AS {{ col.name }}_distinct
            {% if not loop.last %},{% endif %}
            {% endfor %}
        FROM {{ full_table }}
    ),
    quality_summary AS (
        SELECT
            table_name,
            total_rows,
            CORTEX.COMPLETE(
                'claude-3-5-sonnet',
                'Analyze this data quality summary and provide insights:\n\n' ||
                'Table: ' || table_name || '\n' ||
                'Total rows: ' || total_rows || '\n' ||
                -- Add column-specific metrics here
                '\n\nProvide:\n' ||
                '1. Overall quality score (1-10)\n' ||
                '2. Key issues found\n' ||
                '3. Recommended actions\n' ||
                'Be concise.'
            ) AS ai_analysis
        FROM quality_metrics
    )
    SELECT * FROM quality_summary
{% endmacro %}


{% macro cortex_detect_anomalies(table_name, column_name, lookback_days=30) %}
    {#
        Detect anomalies in a numeric column over time.

        Args:
            table_name: Name of the table
            column_name: Numeric column to analyze
            lookback_days: Number of days to analyze

        Returns:
            SQL that identifies potential anomalies
    #}

    {% set schema = target.schema %}
    {% set database = target.database %}
    {% set full_table = database ~ '.' ~ schema ~ '.' ~ table_name %}

    WITH daily_stats AS (
        SELECT
            DATE_TRUNC('day', created_at) AS date,
            AVG({{ column_name }}) AS avg_value,
            STDDEV({{ column_name }}) AS stddev_value,
            COUNT(*) AS row_count
        FROM {{ full_table }}
        WHERE created_at >= DATEADD(day, -{{ lookback_days }}, CURRENT_DATE)
        GROUP BY 1
    ),
    overall_stats AS (
        SELECT
            AVG(avg_value) AS mean,
            STDDEV(avg_value) AS std
        FROM daily_stats
    ),
    anomalies AS (
        SELECT
            d.date,
            d.avg_value,
            d.row_count,
            ABS(d.avg_value - o.mean) / NULLIF(o.std, 0) AS z_score,
            CASE
                WHEN ABS(d.avg_value - o.mean) / NULLIF(o.std, 0) > 2 THEN 'ANOMALY'
                WHEN ABS(d.avg_value - o.mean) / NULLIF(o.std, 0) > 1.5 THEN 'WARNING'
                ELSE 'NORMAL'
            END AS status
        FROM daily_stats d, overall_stats o
    ),
    ai_analysis AS (
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Analyze these daily metrics for {{ column_name }} and identify patterns:\n\n' ||
            (SELECT LISTAGG(date || ': ' || avg_value || ' (z=' || ROUND(z_score, 2) || ', ' || status || ')', '\n')
             FROM anomalies ORDER BY date) ||
            '\n\nProvide:\n' ||
            '1. Any anomalies or concerning patterns\n' ||
            '2. Possible explanations\n' ||
            '3. Recommended investigation steps'
        ) AS analysis
    )
    SELECT
        a.*,
        ai.analysis AS ai_interpretation
    FROM anomalies a, ai_analysis ai
    WHERE a.status != 'NORMAL'
    ORDER BY a.date DESC
{% endmacro %}


{% macro cortex_profile_table(table_name, schema_name=none) %}
    {#
        Generate a comprehensive data profile for a table.

        Args:
            table_name: Name of the table
            schema_name: Optional schema name

        Returns:
            SQL that creates a detailed table profile
    #}

    {% set schema = schema_name or target.schema %}
    {% set database = target.database %}
    {% set full_table = database ~ '.' ~ schema ~ '.' ~ table_name %}

    WITH column_profiles AS (
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM {{ database }}.information_schema.columns
        WHERE table_schema = '{{ schema | upper }}'
          AND table_name = '{{ table_name | upper }}'
        ORDER BY ordinal_position
    ),
    table_stats AS (
        SELECT
            COUNT(*) AS row_count,
            COUNT(*) - COUNT(DISTINCT *) AS duplicate_rows
        FROM {{ full_table }}
    )
    SELECT
        '{{ table_name }}' AS table_name,
        t.row_count,
        t.duplicate_rows,
        (SELECT COUNT(*) FROM column_profiles) AS column_count,
        CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Generate a data profile summary for this table:\n\n' ||
            'Table: {{ table_name }}\n' ||
            'Rows: ' || t.row_count || '\n' ||
            'Potential duplicates: ' || t.duplicate_rows || '\n' ||
            'Columns:\n' ||
            (SELECT LISTAGG(column_name || ' (' || data_type || ')', '\n') FROM column_profiles) ||
            '\n\nProvide a brief profile including:\n' ||
            '1. Table purpose (inferred)\n' ||
            '2. Data completeness assessment\n' ||
            '3. Potential data quality issues\n' ||
            '4. Recommendations'
        ) AS ai_profile
    FROM table_stats t
{% endmacro %}


{% macro cortex_suggest_schema_improvements(table_name) %}
    {#
        Analyze table schema and suggest improvements.

        Args:
            table_name: Name of the table

        Returns:
            AI-generated schema improvement suggestions
    #}

    {% set schema = target.schema %}
    {% set database = target.database %}

    {% set query %}
        WITH schema_info AS (
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                numeric_precision,
                is_nullable,
                column_default
            FROM {{ database }}.information_schema.columns
            WHERE table_schema = '{{ schema | upper }}'
              AND table_name = '{{ table_name | upper }}'
            ORDER BY ordinal_position
        )
        SELECT CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            'Review this table schema and suggest improvements:\n\n' ||
            'Table: {{ table_name }}\n\n' ||
            'Columns:\n' ||
            (SELECT LISTAGG(
                column_name || ': ' || data_type ||
                COALESCE('(' || character_maximum_length || ')', '') ||
                ' nullable=' || is_nullable,
                '\n'
            ) FROM schema_info) ||
            '\n\nConsider:\n' ||
            '1. Data type optimization\n' ||
            '2. Nullable columns that should be NOT NULL\n' ||
            '3. Missing indexes (naming conventions suggest PKs/FKs)\n' ||
            '4. Naming convention improvements\n' ||
            '5. Potential normalization issues\n\n' ||
            'Provide specific, actionable recommendations.'
        ) AS suggestions
    {% endset %}

    {% if execute %}
        {% set result = run_query(query) %}
        {% if result and result.rows %}
            {{ return(result.rows[0][0]) }}
        {% endif %}
    {% endif %}

    {{ return('Schema analysis pending') }}
{% endmacro %}
