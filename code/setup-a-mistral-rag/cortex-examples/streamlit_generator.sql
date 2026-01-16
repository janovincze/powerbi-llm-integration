-- ============================================================================
-- Snowflake Cortex: Streamlit App Generator
-- ============================================================================
-- Generate complete Streamlit applications using Cortex that run natively
-- in Snowflake via "Streamlit in Snowflake" feature.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Example 1: Basic Dashboard App Generator
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Generate a Python Streamlit app for Snowflake (Streamlit in Snowflake) that:

    1. Connects to these tables:
       - SALES(order_id, customer_id, product_category, quantity, unit_price, order_date, region)
       - CUSTOMERS(customer_id, name, segment)

    2. Features:
       - Sidebar filters for date range, region, and customer segment
       - Row of KPI cards showing: Total Revenue, Order Count, Avg Order Value, Unique Customers
       - Line chart showing revenue trend over time
       - Bar chart showing revenue by region
       - Data table with top 10 customers

    3. Requirements:
       - Use st.connection("snowflake") for database connection
       - Use plotly for interactive charts
       - Add proper error handling
       - Include data caching with @st.cache_data

    Return complete, runnable Python code with comments.
    $$
) AS streamlit_app;


-- ----------------------------------------------------------------------------
-- Example 2: Stored Procedure for App Generation
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE generate_streamlit_app(
    app_description VARCHAR,
    table_names ARRAY,
    features ARRAY
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    schema_info VARCHAR DEFAULT '';
    prompt VARCHAR;
    result VARCHAR;
BEGIN
    -- Gather schema information for each table
    FOR i IN 0 TO ARRAY_SIZE(:table_names) - 1 DO
        LET tbl VARCHAR := :table_names[i];

        SELECT CONCAT(
            :schema_info,
            :tbl, '(',
            LISTAGG(column_name || ' ' || data_type, ', ') WITHIN GROUP (ORDER BY ordinal_position),
            ')', CHR(10)
        )
        INTO schema_info
        FROM information_schema.columns
        WHERE table_name = UPPER(:tbl);
    END FOR;

    -- Build the prompt
    prompt := CONCAT(
        'Generate a complete Python Streamlit app for Snowflake (Streamlit in Snowflake).', CHR(10), CHR(10),
        'App Description: ', :app_description, CHR(10), CHR(10),
        'Available Tables:', CHR(10), schema_info, CHR(10),
        'Required Features:', CHR(10), ARRAY_TO_STRING(:features, CHR(10)), CHR(10), CHR(10),
        'Technical Requirements:', CHR(10),
        '- Use st.connection("snowflake") for database access', CHR(10),
        '- Use plotly.express for visualizations', CHR(10),
        '- Implement @st.cache_data for query caching', CHR(10),
        '- Add proper error handling with try/except', CHR(10),
        '- Use st.columns for layout', CHR(10),
        '- Include docstrings and comments', CHR(10), CHR(10),
        'Return complete, production-ready Python code.'
    );

    SELECT CORTEX.COMPLETE('claude-3-5-sonnet', prompt) INTO result;

    -- Clean up the response (remove markdown code blocks if present)
    result := REGEXP_REPLACE(result, '^```python\\s*', '');
    result := REGEXP_REPLACE(result, '\\s*```$', '');

    RETURN result;
END;
$$;

-- Usage:
CALL generate_streamlit_app(
    'Customer analytics dashboard for the sales team',
    ARRAY_CONSTRUCT('SALES', 'CUSTOMERS', 'PRODUCTS'),
    ARRAY_CONSTRUCT(
        'Date range filter',
        'Customer segment filter',
        'Revenue KPI cards',
        'Revenue by product category bar chart',
        'Customer purchase frequency histogram',
        'Downloadable data export'
    )
);


-- ----------------------------------------------------------------------------
-- Example 3: Interactive Data Explorer Generator
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Generate a Streamlit data explorer app for Snowflake with these features:

    1. Table Selection:
       - Dropdown to select from available tables in the current schema
       - Display table metadata (columns, row count, sample data)

    2. Query Builder:
       - Multi-select for columns
       - Filter builder (column, operator, value)
       - Aggregation options (SUM, AVG, COUNT, etc.)
       - GROUP BY selector

    3. Results Display:
       - Paginated data table
       - Auto-generated charts based on data types
       - Download as CSV option

    4. Query History:
       - Store last 10 queries in session state
       - One-click re-run

    Technical notes:
    - Use st.connection("snowflake")
    - Get table list from INFORMATION_SCHEMA
    - Use st.session_state for query history
    - Implement proper SQL injection prevention

    Return complete Python code.
    $$
) AS data_explorer_app;


-- ----------------------------------------------------------------------------
-- Example 4: AI-Powered Analytics App
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Generate a Streamlit app that combines data visualization with Cortex AI analysis.

    Features:
    1. Data Selection:
       - Select table and columns
       - Apply filters
       - Preview data

    2. Visualization:
       - Auto-suggest chart type based on data
       - Interactive plotly charts
       - Chart customization options

    3. AI Analysis (using Cortex):
       - "Analyze this data" button that sends data summary to CORTEX.COMPLETE()
       - Display AI-generated insights
       - "Suggest improvements" for the current visualization
       - Natural language query input ("Show me customers with declining orders")

    4. Export:
       - Export insights as PDF/text
       - Save chart as image
       - Download underlying data

    Use this pattern for Cortex calls within Streamlit:
    ```python
    def get_ai_analysis(data_summary):
        query = f"""
        SELECT CORTEX.COMPLETE('claude-3-5-sonnet',
            'Analyze this data and provide insights: {data_summary}'
        ) as analysis
        """
        return conn.query(query)['ANALYSIS'][0]
    ```

    Return complete Python code with all features.
    $$
) AS ai_analytics_app;


-- ----------------------------------------------------------------------------
-- Example 5: KPI Dashboard Template Generator
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE generate_kpi_dashboard(
    dashboard_title VARCHAR,
    kpi_definitions VARIANT
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    result VARCHAR;
BEGIN
    SELECT CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        CONCAT(
            'Generate a Streamlit KPI dashboard app for Snowflake.', CHR(10), CHR(10),
            'Dashboard Title: ', :dashboard_title, CHR(10), CHR(10),
            'KPI Definitions (JSON):', CHR(10), TO_VARCHAR(:kpi_definitions), CHR(10), CHR(10),
            'For each KPI, create:', CHR(10),
            '- A metric card using st.metric with delta indicator', CHR(10),
            '- A sparkline trend chart below the card', CHR(10),
            '- Conditional formatting (green for positive, red for negative delta)', CHR(10), CHR(10),
            'Layout:', CHR(10),
            '- 4 KPIs per row using st.columns', CHR(10),
            '- Auto-refresh every 5 minutes', CHR(10),
            '- Last updated timestamp in footer', CHR(10), CHR(10),
            'Use st.connection("snowflake") and plotly for charts.',
            CHR(10), 'Return complete Python code.'
        )
    ) INTO result;

    result := REGEXP_REPLACE(result, '^```python\\s*', '');
    result := REGEXP_REPLACE(result, '\\s*```$', '');

    RETURN result;
END;
$$;

-- Usage:
CALL generate_kpi_dashboard(
    'Sales Performance Dashboard',
    PARSE_JSON($$
    [
        {
            "name": "Total Revenue",
            "sql": "SELECT SUM(revenue) FROM sales WHERE order_date >= DATEADD(month, -1, CURRENT_DATE)",
            "sql_previous": "SELECT SUM(revenue) FROM sales WHERE order_date >= DATEADD(month, -2, CURRENT_DATE) AND order_date < DATEADD(month, -1, CURRENT_DATE)",
            "format": "currency"
        },
        {
            "name": "Order Count",
            "sql": "SELECT COUNT(*) FROM sales WHERE order_date >= DATEADD(month, -1, CURRENT_DATE)",
            "sql_previous": "SELECT COUNT(*) FROM sales WHERE order_date >= DATEADD(month, -2, CURRENT_DATE) AND order_date < DATEADD(month, -1, CURRENT_DATE)",
            "format": "number"
        },
        {
            "name": "Avg Order Value",
            "sql": "SELECT AVG(revenue) FROM sales WHERE order_date >= DATEADD(month, -1, CURRENT_DATE)",
            "sql_previous": "SELECT AVG(revenue) FROM sales WHERE order_date >= DATEADD(month, -2, CURRENT_DATE) AND order_date < DATEADD(month, -1, CURRENT_DATE)",
            "format": "currency"
        },
        {
            "name": "New Customers",
            "sql": "SELECT COUNT(DISTINCT customer_id) FROM customers WHERE created_at >= DATEADD(month, -1, CURRENT_DATE)",
            "sql_previous": "SELECT COUNT(DISTINCT customer_id) FROM customers WHERE created_at >= DATEADD(month, -2, CURRENT_DATE) AND created_at < DATEADD(month, -1, CURRENT_DATE)",
            "format": "number"
        }
    ]
    $$)
);


-- ----------------------------------------------------------------------------
-- Example 6: Save Generated Apps to Stage
-- ----------------------------------------------------------------------------

-- Create a stage for storing generated Streamlit apps
CREATE OR REPLACE STAGE streamlit_apps
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Storage for Cortex-generated Streamlit applications';

-- Procedure to generate and save an app
CREATE OR REPLACE PROCEDURE generate_and_save_app(
    app_name VARCHAR,
    app_description VARCHAR,
    tables ARRAY
)
RETURNS VARCHAR
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS
$$
// Generate the app code
var generateStmt = snowflake.createStatement({
    sqlText: `CALL generate_streamlit_app(?, ?, ARRAY_CONSTRUCT(
        'Interactive filters',
        'KPI metrics',
        'Trend visualization',
        'Data table with pagination',
        'CSV export'
    ))`,
    binds: [APP_DESCRIPTION, JSON.stringify(TABLES)]
});

var result = generateStmt.execute();
result.next();
var appCode = result.getColumnValue(1);

// Save to stage
var fileName = APP_NAME.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.py';
var putStmt = snowflake.createStatement({
    sqlText: `PUT 'file://${fileName}' @streamlit_apps AUTO_COMPRESS=FALSE OVERWRITE=TRUE`,
    binds: []
});

// Note: In practice, you'd use a different approach to write to stage
// This is a simplified example

return `App generated: ${fileName}\nCode length: ${appCode.length} characters`;
$$;
