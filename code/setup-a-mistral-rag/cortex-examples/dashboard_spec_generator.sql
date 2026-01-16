-- ============================================================================
-- Snowflake Cortex: Dashboard Specification Generator
-- ============================================================================
-- Generate JSON specifications for PowerBI dashboards using Cortex.
-- These specs can be used with PowerBI REST API or as blueprints for manual
-- dashboard creation.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Example 1: Basic Dashboard Specification
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Generate a JSON specification for a PowerBI dashboard based on this data:

    Schema:
    - SALES(order_id, customer_id, product_id, quantity, unit_price, order_date, region, sales_rep)
    - PRODUCTS(product_id, name, category, cost)
    - CUSTOMERS(customer_id, name, segment, country)

    Requirements:
    - Sales overview dashboard for executive leadership
    - Show key KPIs: Total Revenue, Order Count, Average Order Value, YoY Growth
    - Include regional breakdown
    - Monthly trend visualization
    - Top 10 products table

    Return a JSON object with this structure:
    {
        "dashboard_name": "...",
        "pages": [{
            "name": "...",
            "visuals": [{
                "type": "kpiCard|barChart|lineChart|table|map|pieChart",
                "title": "...",
                "measure": "DAX measure expression",
                "dimensions": ["field1", "field2"],
                "filters": [],
                "position": {"row": 0, "col": 0, "width": 4, "height": 2}
            }]
        }],
        "measures": [{
            "name": "...",
            "dax": "..."
        }],
        "theme": {
            "primaryColor": "#hex",
            "secondaryColor": "#hex"
        }
    }
    $$
) AS dashboard_spec;


-- ----------------------------------------------------------------------------
-- Example 2: Dashboard Generator Stored Procedure
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE generate_dashboard_spec(
    description VARCHAR,
    schema_tables ARRAY,
    style_guidelines VARCHAR DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE SQL
AS
$$
DECLARE
    schema_info VARCHAR DEFAULT '';
    prompt VARCHAR;
    result VARCHAR;
BEGIN
    -- Build schema description from table names
    FOR i IN 0 TO ARRAY_SIZE(:schema_tables) - 1 DO
        LET table_name VARCHAR := :schema_tables[i];

        SELECT CONCAT(
            :schema_info,
            '- ', :table_name, '(',
            LISTAGG(column_name || ' ' || data_type, ', ') WITHIN GROUP (ORDER BY ordinal_position),
            ')', CHR(10)
        )
        INTO schema_info
        FROM information_schema.columns
        WHERE table_name = UPPER(:table_name);
    END FOR;

    -- Build prompt
    prompt := CONCAT(
        'Generate a PowerBI dashboard JSON specification.', CHR(10), CHR(10),
        'Data Schema:', CHR(10), schema_info, CHR(10),
        'Dashboard Requirements:', CHR(10), :description, CHR(10)
    );

    IF (:style_guidelines IS NOT NULL) THEN
        prompt := CONCAT(prompt, CHR(10), 'Style Guidelines:', CHR(10), :style_guidelines);
    END IF;

    prompt := CONCAT(prompt, CHR(10), CHR(10),
        'Return a complete JSON specification with:', CHR(10),
        '1. Dashboard name and description', CHR(10),
        '2. Page layouts with visual specifications', CHR(10),
        '3. DAX measures for all calculations', CHR(10),
        '4. Recommended filters and slicers', CHR(10),
        '5. Color theme recommendations', CHR(10), CHR(10),
        'Return only valid JSON.'
    );

    SELECT CORTEX.COMPLETE('claude-3-5-sonnet', prompt) INTO result;

    -- Parse JSON (remove markdown if present)
    result := REGEXP_REPLACE(result, '^```json\\s*', '');
    result := REGEXP_REPLACE(result, '\\s*```$', '');

    RETURN PARSE_JSON(result);
END;
$$;

-- Usage:
CALL generate_dashboard_spec(
    'Sales performance dashboard showing revenue trends, regional performance, and product analysis',
    ARRAY_CONSTRUCT('SALES', 'PRODUCTS', 'CUSTOMERS'),
    'Use blue color scheme (#0066CC primary), clean minimal design, max 6 visuals per page'
);


-- ----------------------------------------------------------------------------
-- Example 3: Generate DAX Measures for Dashboard
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION generate_dax_measures(
    measure_descriptions ARRAY,
    table_context VARCHAR
)
RETURNS VARIANT
LANGUAGE SQL
AS
$$
    SELECT PARSE_JSON(
        CORTEX.COMPLETE(
            'claude-3-5-sonnet',
            CONCAT(
                'Generate PowerBI DAX measures for these requirements:', CHR(10), CHR(10),
                'Data Context:', CHR(10), table_context, CHR(10), CHR(10),
                'Required Measures:', CHR(10),
                ARRAY_TO_STRING(measure_descriptions, CHR(10)),
                CHR(10), CHR(10),
                'Return a JSON array of objects with "name", "dax", and "description" properties.',
                CHR(10), 'Return only valid JSON array.'
            )
        )
    )
$$;

-- Usage:
SELECT generate_dax_measures(
    ARRAY_CONSTRUCT(
        'Total Revenue - sum of all sales',
        'YoY Growth % - year over year revenue growth',
        'Average Order Value - revenue divided by order count',
        'Customer Lifetime Value - total revenue per customer',
        'Revenue MTD - month to date revenue',
        'Revenue vs Target % - actual vs target comparison'
    ),
    'SALES table with columns: order_date, revenue, customer_id, product_id; TARGETS table with: month, target_amount'
);


-- ----------------------------------------------------------------------------
-- Example 4: Visual Specification Generator
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Generate detailed PowerBI visual specifications for a sales dashboard.

    Available measures:
    - [Total Revenue] = SUM(Sales[Revenue])
    - [Order Count] = COUNTROWS(Sales)
    - [YoY Growth] = ([Total Revenue] - [Total Revenue LY]) / [Total Revenue LY]
    - [Avg Order Value] = DIVIDE([Total Revenue], [Order Count])

    Available dimensions:
    - Date[Year], Date[Quarter], Date[Month], Date[Date]
    - Product[Category], Product[Name]
    - Customer[Segment], Customer[Region], Customer[Country]

    Generate specs for:
    1. KPI cards row (4 cards)
    2. Revenue trend line chart
    3. Regional performance map
    4. Category breakdown bar chart
    5. Top products table

    Return JSON with complete visual configurations including:
    - Visual type
    - Data bindings (measures, dimensions)
    - Formatting (colors, labels, tooltips)
    - Conditional formatting rules
    - Position in grid (12-column layout)
    $$
) AS visual_specs;


-- ----------------------------------------------------------------------------
-- Example 5: Complete Dashboard Package Generator
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE generate_complete_dashboard(
    dashboard_name VARCHAR,
    business_question VARCHAR,
    source_tables ARRAY
)
RETURNS VARIANT
LANGUAGE SQL
AS
$$
DECLARE
    schema_context VARCHAR DEFAULT '';
    dashboard_spec VARIANT;
    dax_measures VARIANT;
    visual_specs VARIANT;
BEGIN
    -- Gather schema information
    FOR i IN 0 TO ARRAY_SIZE(:source_tables) - 1 DO
        LET tbl VARCHAR := :source_tables[i];

        SELECT CONCAT(
            :schema_context,
            :tbl, ': ',
            LISTAGG(column_name || '(' || data_type || ')', ', '),
            CHR(10)
        )
        INTO schema_context
        FROM information_schema.columns
        WHERE table_name = UPPER(:tbl);
    END FOR;

    -- Generate dashboard structure
    SELECT PARSE_JSON(CORTEX.COMPLETE('claude-3-5-sonnet', CONCAT(
        'Design a PowerBI dashboard structure for:', CHR(10),
        'Name: ', :dashboard_name, CHR(10),
        'Business Question: ', :business_question, CHR(10),
        'Available Data: ', :schema_context, CHR(10), CHR(10),
        'Return JSON with: pages array, each with name and list of visual types needed.',
        CHR(10), 'Return only valid JSON.'
    ))) INTO dashboard_spec;

    -- Generate DAX measures
    SELECT PARSE_JSON(CORTEX.COMPLETE('claude-3-5-sonnet', CONCAT(
        'Generate all DAX measures needed for this dashboard:', CHR(10),
        TO_VARCHAR(dashboard_spec), CHR(10),
        'Data: ', :schema_context, CHR(10), CHR(10),
        'Return JSON array of {name, dax, description} objects.',
        CHR(10), 'Return only valid JSON array.'
    ))) INTO dax_measures;

    -- Generate visual specifications
    SELECT PARSE_JSON(CORTEX.COMPLETE('claude-3-5-sonnet', CONCAT(
        'Generate detailed visual specifications for:', CHR(10),
        TO_VARCHAR(dashboard_spec), CHR(10),
        'Using measures: ', TO_VARCHAR(dax_measures), CHR(10), CHR(10),
        'Return JSON array with complete visual configs including position, formatting, data bindings.',
        CHR(10), 'Return only valid JSON array.'
    ))) INTO visual_specs;

    RETURN OBJECT_CONSTRUCT(
        'dashboard_name', :dashboard_name,
        'business_question', :business_question,
        'structure', dashboard_spec,
        'measures', dax_measures,
        'visuals', visual_specs,
        'generated_at', CURRENT_TIMESTAMP()
    );
END;
$$;

-- Usage:
CALL generate_complete_dashboard(
    'Executive Sales Dashboard',
    'How is our sales performance trending and which regions/products need attention?',
    ARRAY_CONSTRUCT('SALES', 'PRODUCTS', 'CUSTOMERS', 'TARGETS')
);


-- ----------------------------------------------------------------------------
-- Example 6: Dashboard to SQL Data Model Generator
-- ----------------------------------------------------------------------------

SELECT CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    $$
    Based on this dashboard specification, generate the SQL views needed in Snowflake
    to support efficient PowerBI DirectQuery or Import mode.

    Dashboard needs:
    - Daily revenue aggregations
    - Customer segment summaries
    - Product performance metrics
    - Regional comparisons
    - YoY calculations

    Source tables:
    - raw_orders (order_id, customer_id, product_id, quantity, price, order_timestamp)
    - raw_customers (customer_id, name, email, segment, region, created_at)
    - raw_products (product_id, sku, name, category, cost)

    Generate:
    1. Dimension views (dim_customer, dim_product, dim_date)
    2. Fact view (fct_sales)
    3. Aggregate views for common dashboard queries
    4. Comments explaining each view's purpose

    Return complete Snowflake SQL statements.
    $$
) AS data_model_sql;
