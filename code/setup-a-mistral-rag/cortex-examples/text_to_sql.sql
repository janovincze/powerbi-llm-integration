-- ============================================================================
-- Snowflake Cortex: Text-to-SQL Examples
-- ============================================================================
-- These examples demonstrate how to use CORTEX.COMPLETE() for SQL generation
-- directly within Snowflake, keeping all data within your security perimeter.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Example 1: Basic Text-to-SQL with Schema Context
-- ----------------------------------------------------------------------------

-- First, create a helper function to get schema information
CREATE OR REPLACE FUNCTION get_table_schema(table_name VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
    SELECT LISTAGG(
        column_name || ' ' || data_type ||
        CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
        ', '
    ) WITHIN GROUP (ORDER BY ordinal_position)
    FROM information_schema.columns
    WHERE table_name = UPPER(table_name)
$$;

-- Generate SQL from natural language
SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    CONCAT(
        'You are a SQL expert. Generate a Snowflake SQL query for the following request.',
        CHR(10), CHR(10),
        'Schema:', CHR(10),
        'SALES(order_id INT, customer_id INT, product_id INT, quantity INT, ',
        'unit_price DECIMAL(10,2), order_date DATE, region VARCHAR)',
        CHR(10), CHR(10),
        'Request: Find the top 10 customers by total revenue in 2024',
        CHR(10), CHR(10),
        'Return only the SQL query, no explanation.'
    )
) AS generated_sql;


-- ----------------------------------------------------------------------------
-- Example 2: Dynamic Schema Retrieval
-- ----------------------------------------------------------------------------

-- Create a stored procedure for text-to-SQL with dynamic schema
CREATE OR REPLACE PROCEDURE generate_sql_from_question(
    table_name VARCHAR,
    question VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    schema_info VARCHAR;
    prompt VARCHAR;
    result VARCHAR;
BEGIN
    -- Get schema dynamically
    SELECT LISTAGG(
        column_name || ' ' || data_type,
        ', '
    ) WITHIN GROUP (ORDER BY ordinal_position)
    INTO schema_info
    FROM information_schema.columns
    WHERE table_name = UPPER(:table_name);

    -- Build prompt
    prompt := CONCAT(
        'You are a SQL expert for Snowflake. Generate a SQL query.',
        CHR(10), CHR(10),
        'Table: ', :table_name, CHR(10),
        'Columns: ', schema_info,
        CHR(10), CHR(10),
        'Question: ', :question,
        CHR(10), CHR(10),
        'Return only valid Snowflake SQL, no markdown or explanation.'
    );

    -- Generate SQL
    SELECT CORTEX.COMPLETE('claude-3-5-sonnet', prompt) INTO result;

    RETURN result;
END;
$$;

-- Usage:
CALL generate_sql_from_question('SALES', 'What is the average order value by region?');


-- ----------------------------------------------------------------------------
-- Example 3: Multi-Table Query Generation
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    You are a SQL expert. Generate a Snowflake SQL query.

    Schema:
    - CUSTOMERS(customer_id INT PK, name VARCHAR, email VARCHAR, segment VARCHAR, created_at TIMESTAMP)
    - ORDERS(order_id INT PK, customer_id INT FK, order_date DATE, total_amount DECIMAL, status VARCHAR)
    - ORDER_ITEMS(item_id INT PK, order_id INT FK, product_id INT FK, quantity INT, unit_price DECIMAL)
    - PRODUCTS(product_id INT PK, name VARCHAR, category VARCHAR, cost DECIMAL)

    Request: Find customers who have placed more than 5 orders in the last 90 days,
    show their name, email, order count, and total spend, ordered by total spend descending.

    Return only the SQL query.
    $$
) AS generated_sql;


-- ----------------------------------------------------------------------------
-- Example 4: SQL Generation with Business Context
-- ----------------------------------------------------------------------------

-- Create a table to store business definitions
CREATE OR REPLACE TABLE business_glossary (
    term VARCHAR,
    definition VARCHAR,
    sql_logic VARCHAR
);

INSERT INTO business_glossary VALUES
    ('Active Customer', 'Customer with at least one order in last 90 days',
     'customer_id IN (SELECT customer_id FROM orders WHERE order_date >= DATEADD(day, -90, CURRENT_DATE))'),
    ('High Value Customer', 'Customer with lifetime spend > $10,000',
     'customer_id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING SUM(total_amount) > 10000)'),
    ('Churn Risk', 'Previously active customer with no orders in 60+ days',
     'customer_id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING MAX(order_date) < DATEADD(day, -60, CURRENT_DATE) AND MAX(order_date) >= DATEADD(day, -180, CURRENT_DATE))');

-- Generate SQL using business context
CREATE OR REPLACE PROCEDURE generate_sql_with_context(question VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    glossary_context VARCHAR;
    result VARCHAR;
BEGIN
    -- Get relevant business definitions
    SELECT LISTAGG(
        term || ': ' || definition || ' (SQL: ' || sql_logic || ')',
        CHR(10)
    ) INTO glossary_context
    FROM business_glossary;

    SELECT CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        CONCAT(
            'Generate a Snowflake SQL query using these business definitions:', CHR(10),
            glossary_context, CHR(10), CHR(10),
            'Schema: CUSTOMERS(customer_id, name, email, segment), ',
            'ORDERS(order_id, customer_id, order_date, total_amount)', CHR(10), CHR(10),
            'Question: ', :question, CHR(10), CHR(10),
            'Use the business definitions when applicable. Return only SQL.'
        )
    ) INTO result;

    RETURN result;
END;
$$;

-- Usage:
CALL generate_sql_with_context('List all high value customers who are at churn risk');


-- ----------------------------------------------------------------------------
-- Example 5: Query Explanation (Reverse: SQL to Natural Language)
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Explain what this SQL query does in plain English for a business analyst:

    SELECT
        c.segment,
        COUNT(DISTINCT c.customer_id) as customer_count,
        SUM(o.total_amount) as total_revenue,
        SUM(o.total_amount) / COUNT(DISTINCT c.customer_id) as revenue_per_customer
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_date >= DATEADD(year, -1, CURRENT_DATE)
    GROUP BY c.segment
    HAVING COUNT(DISTINCT c.customer_id) >= 10
    ORDER BY total_revenue DESC;

    Provide a clear, concise explanation.
    $$
) AS explanation;


-- ----------------------------------------------------------------------------
-- Example 6: Query Optimization Suggestions
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Review this Snowflake SQL query and suggest optimizations:

    SELECT *
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE YEAR(o.order_date) = 2024
    AND c.segment = 'Enterprise'
    ORDER BY o.order_date DESC;

    Consider:
    1. Column selection (SELECT *)
    2. Filter optimization
    3. Join order
    4. Potential clustering keys

    Provide specific, actionable recommendations.
    $$
) AS optimization_suggestions;
