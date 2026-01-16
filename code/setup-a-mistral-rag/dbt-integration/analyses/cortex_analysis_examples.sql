/*
 * Cortex Analysis Examples
 *
 * This file contains example queries showing how to use Snowflake Cortex
 * for ad-hoc analysis within a dbt project.
 *
 * These queries can be run directly or adapted into models/macros.
 */


-- ============================================================================
-- Example 1: Generate insights from sales data
-- ============================================================================

WITH monthly_sales AS (
    SELECT
        DATE_TRUNC('month', date_day) AS month,
        customer_segment,
        SUM(total_revenue) AS revenue,
        SUM(order_count) AS orders
    FROM {{ ref('mart_daily_sales') }}
    WHERE date_day >= DATEADD(month, -6, CURRENT_DATE)
    GROUP BY 1, 2
)
SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this sales data and provide business insights:\n\n' ||
    (SELECT LISTAGG(
        month::VARCHAR || ' | ' || customer_segment || ' | $' || revenue::VARCHAR || ' | ' || orders || ' orders',
        '\n'
    ) FROM monthly_sales) ||
    '\n\nProvide:\n' ||
    '1. Key trends observed\n' ||
    '2. Segment performance comparison\n' ||
    '3. Actionable recommendations'
) AS sales_insights;


-- ============================================================================
-- Example 2: Anomaly explanation
-- ============================================================================

WITH daily_revenue AS (
    SELECT
        date_day,
        SUM(total_revenue) AS revenue
    FROM {{ ref('mart_daily_sales') }}
    WHERE date_day >= DATEADD(day, -30, CURRENT_DATE)
    GROUP BY 1
),
stats AS (
    SELECT
        AVG(revenue) AS avg_revenue,
        STDDEV(revenue) AS std_revenue
    FROM daily_revenue
),
anomalies AS (
    SELECT
        d.date_day,
        d.revenue,
        (d.revenue - s.avg_revenue) / NULLIF(s.std_revenue, 0) AS z_score
    FROM daily_revenue d, stats s
    WHERE ABS((d.revenue - s.avg_revenue) / NULLIF(s.std_revenue, 0)) > 2
)
SELECT
    a.date_day,
    a.revenue,
    a.z_score,
    CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        'This date showed anomalous revenue:\n' ||
        'Date: ' || a.date_day::VARCHAR || '\n' ||
        'Revenue: $' || a.revenue::VARCHAR || '\n' ||
        'Z-score: ' || ROUND(a.z_score, 2)::VARCHAR || '\n' ||
        'Average revenue: $' || (SELECT ROUND(avg_revenue, 2) FROM stats)::VARCHAR || '\n\n' ||
        'What are the most likely business explanations for this anomaly? ' ||
        'Consider: promotions, holidays, external events, data issues.'
    ) AS explanation
FROM anomalies a;


-- ============================================================================
-- Example 3: Customer segmentation analysis
-- ============================================================================

WITH customer_metrics AS (
    SELECT
        customer_segment,
        COUNT(DISTINCT customer_id) AS customers,
        SUM(total_revenue) / COUNT(DISTINCT customer_id) AS revenue_per_customer,
        SUM(order_count) / COUNT(DISTINCT customer_id) AS orders_per_customer
    FROM {{ ref('fct_orders') }}
    WHERE order_date >= DATEADD(year, -1, CURRENT_DATE)
    GROUP BY 1
)
SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze these customer segments and provide strategic recommendations:\n\n' ||
    (SELECT LISTAGG(
        customer_segment || ': ' ||
        customers || ' customers, ' ||
        '$' || ROUND(revenue_per_customer, 2) || ' rev/customer, ' ||
        ROUND(orders_per_customer, 1) || ' orders/customer',
        '\n'
    ) FROM customer_metrics) ||
    '\n\nProvide:\n' ||
    '1. Segment health assessment\n' ||
    '2. Growth opportunities\n' ||
    '3. Recommended strategies per segment'
) AS segmentation_analysis;


-- ============================================================================
-- Example 4: Generate SQL from natural language
-- ============================================================================

-- Use Cortex to generate a query, then execute it
WITH generated AS (
    SELECT CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        'Generate a Snowflake SQL query to find:\n' ||
        'The top 10 customers by total revenue in the last 90 days, ' ||
        'showing their name, segment, total revenue, order count, and average order value.\n\n' ||
        'Use these tables:\n' ||
        '- fct_orders (customer_id, revenue, order_date, order_count)\n' ||
        '- dim_customers (customer_id, customer_name, segment)\n\n' ||
        'Return only the SQL query.'
    ) AS generated_sql
)
-- In practice, you would review and then execute the generated SQL
SELECT generated_sql FROM generated;


-- ============================================================================
-- Example 5: Data quality narrative
-- ============================================================================

WITH quality_metrics AS (
    SELECT
        'fct_orders' AS table_name,
        COUNT(*) AS total_rows,
        COUNT(*) - COUNT(customer_id) AS null_customer_ids,
        COUNT(*) - COUNT(revenue) AS null_revenues,
        COUNT(CASE WHEN revenue < 0 THEN 1 END) AS negative_revenues,
        COUNT(CASE WHEN order_date > CURRENT_DATE THEN 1 END) AS future_dates
    FROM {{ ref('fct_orders') }}
)
SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Generate a data quality report narrative:\n\n' ||
    'Table: ' || table_name || '\n' ||
    'Total rows: ' || total_rows || '\n' ||
    'Null customer_ids: ' || null_customer_ids || '\n' ||
    'Null revenues: ' || null_revenues || '\n' ||
    'Negative revenues: ' || negative_revenues || '\n' ||
    'Future dates: ' || future_dates || '\n\n' ||
    'Write a brief data quality summary suitable for a weekly report. ' ||
    'Highlight any concerns and recommended actions.'
) AS quality_narrative
FROM quality_metrics;


-- ============================================================================
-- Example 6: Compare model documentation with actual data
-- ============================================================================

WITH documented AS (
    -- This would come from your YAML in practice
    SELECT
        'dim_customers' AS model,
        'segment' AS column_name,
        'Customer segment: Enterprise, SMB, or Consumer' AS documented_values
),
actual AS (
    SELECT DISTINCT segment AS actual_value
    FROM {{ ref('dim_customers') }}
)
SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Compare documented vs actual values:\n\n' ||
    'Column: ' || d.column_name || '\n' ||
    'Documentation says: ' || d.documented_values || '\n' ||
    'Actual values found: ' || (SELECT LISTAGG(actual_value, ', ') FROM actual) || '\n\n' ||
    'Are these consistent? Flag any discrepancies and suggest documentation updates.'
) AS documentation_check
FROM documented d;


-- ============================================================================
-- Example 7: Generate dbt test suggestions
-- ============================================================================

WITH column_analysis AS (
    SELECT
        'fct_orders' AS table_name,
        'customer_id' AS column_name,
        COUNT(*) AS total_rows,
        COUNT(customer_id) AS non_null_count,
        COUNT(DISTINCT customer_id) AS distinct_count,
        MIN(customer_id)::VARCHAR AS min_value,
        MAX(customer_id)::VARCHAR AS max_value
    FROM {{ ref('fct_orders') }}
)
SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Based on this column analysis, suggest dbt tests:\n\n' ||
    'Table: ' || table_name || '\n' ||
    'Column: ' || column_name || '\n' ||
    'Total rows: ' || total_rows || '\n' ||
    'Non-null: ' || non_null_count || '\n' ||
    'Distinct values: ' || distinct_count || '\n' ||
    'Range: ' || min_value || ' to ' || max_value || '\n\n' ||
    'Suggest appropriate dbt tests from: not_null, unique, accepted_values, relationships.\n' ||
    'Return as YAML format ready to paste into schema.yml.'
) AS test_suggestions
FROM column_analysis;
