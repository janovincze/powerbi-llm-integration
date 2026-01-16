-- ============================================================================
-- Snowflake Cortex: Iterative SQL Refinement
-- ============================================================================
-- This file demonstrates how to use Cortex for iterative query refinement,
-- where the LLM can see query results and improve the SQL across multiple
-- iterations—all within Snowflake's secure perimeter.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Setup: Create sample data for demonstration
-- ----------------------------------------------------------------------------

CREATE OR REPLACE TABLE demo_sales (
    order_id INT,
    customer_id INT,
    product_category VARCHAR,
    quantity INT,
    unit_price DECIMAL(10,2),
    order_date DATE,
    region VARCHAR
);

INSERT INTO demo_sales VALUES
    (1, 101, 'Electronics', 2, 599.99, '2024-01-15', 'North'),
    (2, 102, 'Electronics', 1, 1299.99, '2024-01-16', 'South'),
    (3, 101, 'Accessories', 5, 29.99, '2024-01-17', 'North'),
    (4, 103, 'Electronics', 1, 899.99, '2024-02-01', 'East'),
    (5, 104, 'Furniture', 1, 1499.99, '2024-02-15', 'West'),
    (6, 102, 'Electronics', 2, 449.99, '2024-03-01', 'South'),
    (7, 105, 'Accessories', 10, 19.99, '2024-03-10', 'North'),
    (8, 101, 'Furniture', 1, 2199.99, '2024-03-15', 'North'),
    (9, 106, 'Electronics', 1, 799.99, '2024-04-01', 'East'),
    (10, 103, 'Accessories', 3, 49.99, '2024-04-10', 'East');


-- ----------------------------------------------------------------------------
-- Example 1: Basic Iterative Refinement Pattern
-- ----------------------------------------------------------------------------

-- Step 1: Generate initial SQL
CREATE OR REPLACE TEMPORARY TABLE iteration_1 AS
SELECT
    CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        $$
        Generate a Snowflake SQL query for this request:

        Table: demo_sales(order_id, customer_id, product_category, quantity, unit_price, order_date, region)

        Question: Find products with declining sales trends

        Return only the SQL query.
        $$
    ) AS generated_sql,
    1 AS iteration_num,
    CURRENT_TIMESTAMP() AS generated_at;

SELECT * FROM iteration_1;

-- Step 2: Execute the generated SQL and capture results
-- (In practice, you'd use dynamic SQL or a stored procedure)
-- For demo, let's assume the first query returned unexpected results

-- Step 3: Refine based on feedback
CREATE OR REPLACE TEMPORARY TABLE iteration_2 AS
SELECT
    CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        $$
        The previous SQL query for "Find products with declining sales" returned this:

        Previous SQL:
        SELECT product_category, SUM(quantity) as total_qty
        FROM demo_sales
        GROUP BY product_category
        ORDER BY total_qty DESC;

        Results:
        | product_category | total_qty |
        |-----------------|-----------|
        | Accessories     | 18        |
        | Electronics     | 7         |
        | Furniture       | 2         |

        Issue: This just shows total quantities, not trends over time.

        Please generate improved SQL that:
        1. Compares sales between time periods (e.g., month over month)
        2. Identifies categories where recent sales are LOWER than previous periods
        3. Shows the percentage decline

        Return only the improved SQL query.
        $$
    ) AS generated_sql,
    2 AS iteration_num,
    CURRENT_TIMESTAMP() AS generated_at;

SELECT * FROM iteration_2;


-- ----------------------------------------------------------------------------
-- Example 2: Stored Procedure for Automated Iteration
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE iterative_sql_generator(
    question VARCHAR,
    table_schema VARCHAR,
    max_iterations INT DEFAULT 3
)
RETURNS VARIANT
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS
$$
var iterations = [];
var currentSql = '';
var feedback = '';

for (var i = 1; i <= MAX_ITERATIONS; i++) {
    // Build prompt
    var prompt = '';
    if (i === 1) {
        prompt = `Generate a Snowflake SQL query.

Schema: ${TABLE_SCHEMA}

Question: ${QUESTION}

Return only valid SQL, no explanation.`;
    } else {
        prompt = `Previous SQL attempt:
${currentSql}

Feedback: ${feedback}

Generate an improved SQL query that addresses the feedback.
Return only valid SQL, no explanation.`;
    }

    // Generate SQL using Cortex
    var generateStmt = snowflake.createStatement({
        sqlText: `SELECT CORTEX.COMPLETE('claude-3-5-sonnet', ?) AS sql_result`,
        binds: [prompt]
    });
    var generateResult = generateStmt.execute();
    generateResult.next();
    currentSql = generateResult.getColumnValue('SQL_RESULT');

    // Clean the SQL (remove markdown if present)
    currentSql = currentSql.replace(/```sql\n?/g, '').replace(/```\n?/g, '').trim();

    // Try to execute the SQL
    var success = false;
    var resultSummary = '';
    var errorMsg = '';

    try {
        var execStmt = snowflake.createStatement({sqlText: currentSql});
        var execResult = execStmt.execute();

        // Get result summary
        var rowCount = 0;
        var columns = [];
        for (var c = 1; c <= execResult.getColumnCount(); c++) {
            columns.push(execResult.getColumnName(c));
        }

        var sampleRows = [];
        while (execResult.next() && rowCount < 5) {
            var row = {};
            for (var c = 1; c <= execResult.getColumnCount(); c++) {
                row[execResult.getColumnName(c)] = execResult.getColumnValue(c);
            }
            sampleRows.push(row);
            rowCount++;
        }

        // Continue counting remaining rows
        while (execResult.next()) {
            rowCount++;
        }

        resultSummary = `Returned ${rowCount} rows. Columns: ${columns.join(', ')}. Sample: ${JSON.stringify(sampleRows)}`;
        success = true;

    } catch (err) {
        errorMsg = err.message;
        feedback = `SQL Error: ${errorMsg}. Please fix the syntax.`;
    }

    // Store iteration result
    iterations.push({
        iteration: i,
        sql: currentSql,
        success: success,
        result_summary: resultSummary,
        error: errorMsg
    });

    // If successful, analyze results for quality
    if (success && i < MAX_ITERATIONS) {
        var analyzePrompt = `Analyze if this SQL result answers the question adequately.

Question: ${QUESTION}
SQL: ${currentSql}
Results: ${resultSummary}

If the results are satisfactory, respond with: SATISFACTORY
If improvements are needed, respond with: NEEDS_IMPROVEMENT: [specific feedback]`;

        var analyzeStmt = snowflake.createStatement({
            sqlText: `SELECT CORTEX.COMPLETE('claude-3-5-sonnet', ?) AS analysis`,
            binds: [analyzePrompt]
        });
        var analyzeResult = analyzeStmt.execute();
        analyzeResult.next();
        var analysis = analyzeResult.getColumnValue('ANALYSIS');

        if (analysis.indexOf('SATISFACTORY') >= 0) {
            break; // Done!
        } else {
            feedback = analysis.replace('NEEDS_IMPROVEMENT:', '').trim();
        }
    }
}

return {
    question: QUESTION,
    final_sql: currentSql,
    total_iterations: iterations.length,
    iterations: iterations
};
$$;

-- Usage:
CALL iterative_sql_generator(
    'Find the top 3 customers by revenue who have purchased from multiple product categories',
    'demo_sales(order_id, customer_id, product_category, quantity, unit_price, order_date, region)',
    3
);


-- ----------------------------------------------------------------------------
-- Example 3: Refinement with Data Quality Checks
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE refine_with_quality_checks(
    initial_question VARCHAR,
    table_name VARCHAR
)
RETURNS TABLE(
    iteration INT,
    sql_query VARCHAR,
    row_count INT,
    null_percentage FLOAT,
    quality_issues VARCHAR,
    is_final BOOLEAN
)
LANGUAGE SQL
AS
$$
DECLARE
    current_sql VARCHAR;
    schema_info VARCHAR;
    iteration_num INT DEFAULT 1;
    result_cursor CURSOR FOR SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
BEGIN
    -- Get schema
    SELECT LISTAGG(column_name || ' ' || data_type, ', ')
    INTO schema_info
    FROM information_schema.columns
    WHERE table_name = UPPER(:table_name);

    -- Generate initial SQL
    SELECT CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        CONCAT(
            'Generate SQL for: ', :initial_question, CHR(10),
            'Schema: ', :table_name, '(', schema_info, ')', CHR(10),
            'Return only SQL.'
        )
    ) INTO current_sql;

    -- Create results table
    CREATE OR REPLACE TEMPORARY TABLE refinement_results (
        iteration INT,
        sql_query VARCHAR,
        row_count INT,
        null_percentage FLOAT,
        quality_issues VARCHAR,
        is_final BOOLEAN
    );

    -- Would continue with execution and quality checks...
    -- (Simplified for demonstration)

    INSERT INTO refinement_results VALUES (1, current_sql, NULL, NULL, 'Initial generation', FALSE);

    RETURN TABLE(SELECT * FROM refinement_results);
END;
$$;


-- ----------------------------------------------------------------------------
-- Example 4: Human-in-the-Loop Refinement Table
-- ----------------------------------------------------------------------------

-- Create a table to track refinement sessions
CREATE OR REPLACE TABLE sql_refinement_sessions (
    session_id VARCHAR DEFAULT UUID_STRING(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    original_question VARCHAR,
    table_schema VARCHAR,
    status VARCHAR DEFAULT 'in_progress'
);

CREATE OR REPLACE TABLE sql_refinement_iterations (
    iteration_id VARCHAR DEFAULT UUID_STRING(),
    session_id VARCHAR,
    iteration_num INT,
    generated_sql VARCHAR,
    execution_success BOOLEAN,
    result_summary VARCHAR,
    human_feedback VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Start a new session
INSERT INTO sql_refinement_sessions (original_question, table_schema)
VALUES (
    'Find customers at risk of churning based on declining purchase frequency',
    'customers(id, name, segment), orders(id, customer_id, order_date, amount)'
);

-- Generate first iteration
INSERT INTO sql_refinement_iterations (session_id, iteration_num, generated_sql)
SELECT
    s.session_id,
    1,
    CORTEX.COMPLETE('claude-3-5-sonnet', CONCAT(
        'Generate SQL for: ', s.original_question, CHR(10),
        'Schema: ', s.table_schema
    ))
FROM sql_refinement_sessions s
WHERE s.status = 'in_progress'
ORDER BY s.created_at DESC
LIMIT 1;

-- After human reviews and provides feedback, generate next iteration
-- UPDATE sql_refinement_iterations
-- SET human_feedback = 'Need to compare current 30 days vs previous 30 days'
-- WHERE iteration_id = '...';

-- View session history
SELECT
    s.original_question,
    i.iteration_num,
    i.generated_sql,
    i.human_feedback,
    i.created_at
FROM sql_refinement_sessions s
JOIN sql_refinement_iterations i ON s.session_id = i.session_id
ORDER BY s.created_at DESC, i.iteration_num;
