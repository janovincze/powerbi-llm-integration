{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        tags=['facts', 'daily'],
        cluster_by=['order_date']
    )
}}

/*
    Fact table for orders.

    Grain: One row per order
    Update frequency: Incremental (hourly)

    This model:
    - Joins order data with customer and product dimensions
    - Calculates derived metrics (revenue, margin)
    - Applies business logic for order status
    - Supports incremental processing for efficiency

    {{ cortex_describe_model(model.raw_sql) }}
*/

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
    -- Only process new/updated orders in incremental runs
    -- Include 3-day lookback for late-arriving data
    WHERE updated_at > (SELECT DATEADD(day, -3, MAX(updated_at)) FROM {{ this }})
    {% endif %}
),

order_items AS (
    SELECT * FROM {{ ref('stg_order_items') }}
),

customers AS (
    SELECT * FROM {{ ref('dim_customers') }}
),

products AS (
    SELECT * FROM {{ ref('dim_products') }}
),

-- Aggregate order items to order level
order_line_agg AS (
    SELECT
        order_id,
        SUM(quantity) AS total_quantity,
        SUM(quantity * unit_price) AS gross_revenue,
        SUM(quantity * unit_cost) AS total_cost,
        COUNT(DISTINCT product_id) AS distinct_products
    FROM order_items oi
    LEFT JOIN products p ON oi.product_id = p.product_id
    GROUP BY 1
),

-- Build the fact table
final AS (
    SELECT
        -- Keys
        o.order_id,
        o.customer_id,
        o.order_date,

        -- Customer attributes (for analysis without joins)
        c.segment AS customer_segment,
        c.region AS customer_region,

        -- Order metrics
        ola.total_quantity,
        ola.gross_revenue AS revenue,
        ola.total_cost,
        ola.gross_revenue - ola.total_cost AS gross_margin,
        CASE
            WHEN ola.gross_revenue > 0
            THEN (ola.gross_revenue - ola.total_cost) / ola.gross_revenue
            ELSE 0
        END AS margin_percent,
        ola.distinct_products,

        -- Order attributes
        o.status AS order_status,
        o.channel AS order_channel,
        o.promotion_code,
        CASE WHEN o.promotion_code IS NOT NULL THEN TRUE ELSE FALSE END AS has_promotion,

        -- Time dimensions
        DATE_TRUNC('month', o.order_date) AS order_month,
        DATE_TRUNC('quarter', o.order_date) AS order_quarter,
        YEAR(o.order_date) AS order_year,
        DAYOFWEEK(o.order_date) AS day_of_week,
        CASE WHEN DAYOFWEEK(o.order_date) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,

        -- Customer history at time of order
        DATEDIFF('day', c.first_order_date, o.order_date) AS customer_tenure_days,
        CASE
            WHEN DATEDIFF('day', c.first_order_date, o.order_date) = 0 THEN 'New'
            WHEN DATEDIFF('day', c.first_order_date, o.order_date) <= 30 THEN 'Early'
            WHEN DATEDIFF('day', c.first_order_date, o.order_date) <= 365 THEN 'Established'
            ELSE 'Loyal'
        END AS customer_lifecycle_stage,

        -- Metadata
        o.created_at,
        o.updated_at,
        CURRENT_TIMESTAMP() AS dbt_updated_at

    FROM orders o
    LEFT JOIN order_line_agg ola ON o.order_id = ola.order_id
    LEFT JOIN customers c ON o.customer_id = c.customer_id

    -- Data quality filter
    WHERE o.order_id IS NOT NULL
      AND o.order_date IS NOT NULL
      AND ola.gross_revenue > 0  -- Exclude zero-value orders
)

SELECT * FROM final
