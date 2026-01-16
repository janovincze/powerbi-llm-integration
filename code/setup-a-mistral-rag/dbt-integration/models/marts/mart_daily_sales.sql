{{
    config(
        materialized='table',
        tags=['marts', 'daily', 'powerbi'],
        post_hook=[
            "GRANT SELECT ON {{ this }} TO ROLE POWERBI_READER"
        ]
    )
}}

/*
    Daily Sales Mart

    Purpose: Pre-aggregated sales data optimized for PowerBI dashboards
    Grain: One row per day × product category × region
    Refresh: Daily (full rebuild)

    Consumers:
    - Sales Overview Dashboard
    - Regional Performance Report
    - Executive KPI Cards

    Notes:
    - Includes prior period comparisons for YoY calculations
    - Materialized as table for fast dashboard queries
    - Clustered by date for time-series queries
*/

WITH daily_orders AS (
    SELECT
        order_date AS date_day,
        customer_segment,
        customer_region,
        COUNT(DISTINCT order_id) AS order_count,
        COUNT(DISTINCT customer_id) AS customer_count,
        SUM(revenue) AS total_revenue,
        SUM(gross_margin) AS total_margin,
        SUM(total_quantity) AS total_units,
        AVG(revenue) AS avg_order_value
    FROM {{ ref('fct_orders') }}
    WHERE order_status NOT IN ('cancelled', 'refunded')
    GROUP BY 1, 2, 3
),

-- Add date spine for complete time series
date_spine AS (
    SELECT date_day
    FROM {{ ref('dim_date') }}
    WHERE date_day >= DATEADD(year, -2, CURRENT_DATE)
      AND date_day < CURRENT_DATE
),

-- All segment/region combinations
dimensions AS (
    SELECT DISTINCT
        customer_segment,
        customer_region
    FROM {{ ref('fct_orders') }}
),

-- Complete grid
complete_grid AS (
    SELECT
        ds.date_day,
        d.customer_segment,
        d.customer_region
    FROM date_spine ds
    CROSS JOIN dimensions d
),

-- Join actuals to complete grid
with_actuals AS (
    SELECT
        cg.date_day,
        cg.customer_segment,
        cg.customer_region,
        COALESCE(do.order_count, 0) AS order_count,
        COALESCE(do.customer_count, 0) AS customer_count,
        COALESCE(do.total_revenue, 0) AS total_revenue,
        COALESCE(do.total_margin, 0) AS total_margin,
        COALESCE(do.total_units, 0) AS total_units,
        do.avg_order_value
    FROM complete_grid cg
    LEFT JOIN daily_orders do
        ON cg.date_day = do.date_day
        AND cg.customer_segment = do.customer_segment
        AND cg.customer_region = do.customer_region
),

-- Add prior period for comparisons
with_prior_period AS (
    SELECT
        wa.*,

        -- Prior year same day
        LAG(total_revenue, 365) OVER (
            PARTITION BY customer_segment, customer_region
            ORDER BY date_day
        ) AS revenue_ly,

        LAG(order_count, 365) OVER (
            PARTITION BY customer_segment, customer_region
            ORDER BY date_day
        ) AS orders_ly,

        -- Prior month
        LAG(total_revenue, 30) OVER (
            PARTITION BY customer_segment, customer_region
            ORDER BY date_day
        ) AS revenue_pm,

        -- Running totals
        SUM(total_revenue) OVER (
            PARTITION BY customer_segment, customer_region,
                         DATE_TRUNC('month', date_day)
            ORDER BY date_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS revenue_mtd,

        SUM(total_revenue) OVER (
            PARTITION BY customer_segment, customer_region,
                         DATE_TRUNC('year', date_day)
            ORDER BY date_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS revenue_ytd

    FROM with_actuals wa
),

final AS (
    SELECT
        -- Dimensions
        date_day,
        customer_segment,
        customer_region,

        -- Date attributes for filtering
        DATE_TRUNC('week', date_day) AS week_start,
        DATE_TRUNC('month', date_day) AS month_start,
        DATE_TRUNC('quarter', date_day) AS quarter_start,
        YEAR(date_day) AS year_num,
        MONTH(date_day) AS month_num,
        DAYOFWEEK(date_day) AS day_of_week,

        -- Current period metrics
        order_count,
        customer_count,
        total_revenue,
        total_margin,
        total_units,
        avg_order_value,

        -- Period over period
        revenue_ly,
        orders_ly,
        revenue_pm,

        -- YoY calculations
        CASE
            WHEN revenue_ly > 0
            THEN (total_revenue - revenue_ly) / revenue_ly
            ELSE NULL
        END AS revenue_yoy_growth,

        -- Running totals
        revenue_mtd,
        revenue_ytd,

        -- Margin percentage
        CASE
            WHEN total_revenue > 0
            THEN total_margin / total_revenue
            ELSE NULL
        END AS margin_percent,

        -- Metadata
        CURRENT_TIMESTAMP() AS dbt_updated_at

    FROM with_prior_period
)

SELECT * FROM final
