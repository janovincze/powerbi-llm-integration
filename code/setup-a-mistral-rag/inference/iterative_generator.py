"""
Iterative SQL Generator for Self-Hosted Mistral

This module provides iterative SQL generation with full data access.
Because the LLM runs locally, you can safely show it query results
and let it improve - no data leaves your infrastructure.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    """Result of a single iteration."""
    sql: str
    success: bool
    results: Optional[pd.DataFrame] = None
    results_summary: Optional[str] = None
    error: Optional[str] = None
    issues: Optional[str] = None
    suggestions: Optional[str] = None


@dataclass
class GenerationResult:
    """Final result of iterative generation."""
    sql: str
    results: Optional[pd.DataFrame]
    iterations: int
    history: List[IterationResult]
    satisfactory: bool


class IterativeSQLGenerator:
    """
    Generate SQL with iterative refinement based on actual results.

    Safe because everything runs locally - no data leaves your infrastructure.
    The LLM can see full query results and improve based on actual data.
    """

    def __init__(
        self,
        llm_client,
        snowflake_connection,
        max_iterations: int = 3,
        model_name: str = "mistral-7b-sql"
    ):
        """
        Initialize the generator.

        Args:
            llm_client: Client for the local LLM (e.g., vLLM, Ollama)
            snowflake_connection: Snowflake connection object
            max_iterations: Maximum number of refinement iterations
            model_name: Name of the fine-tuned model
        """
        self.llm = llm_client
        self.conn = snowflake_connection
        self.max_iterations = max_iterations
        self.model_name = model_name

    def generate_with_refinement(
        self,
        question: str,
        schema: str,
        validation_fn: Optional[Callable] = None
    ) -> GenerationResult:
        """
        Generate SQL with iterative refinement based on actual results.

        Args:
            question: Natural language question
            schema: Database schema description
            validation_fn: Optional function to validate results (returns bool)

        Returns:
            GenerationResult with final SQL, results, and history
        """
        history: List[IterationResult] = []
        current_sql = ""
        current_results = None
        satisfactory = False

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Starting iteration {iteration}")

            # Build prompt with history
            prompt = self._build_prompt(question, schema, history)

            # Generate SQL
            current_sql = self._generate_sql(prompt)
            logger.info(f"Generated SQL: {current_sql[:100]}...")

            # Execute and get results
            try:
                current_results = self._execute_query(current_sql)

                # Analyze results for quality
                analysis = self._analyze_results(question, current_results)

                iteration_result = IterationResult(
                    sql=current_sql,
                    success=True,
                    results=current_results,
                    results_summary=self._summarize_results(current_results),
                    issues=analysis.get("issues"),
                    suggestions=analysis.get("suggestions")
                )

                # Check if satisfactory
                if analysis.get("satisfactory", False):
                    satisfactory = True
                    history.append(iteration_result)
                    logger.info("Results are satisfactory, stopping iteration")
                    break

                # Additional validation if provided
                if validation_fn and validation_fn(current_results):
                    satisfactory = True
                    history.append(iteration_result)
                    logger.info("Custom validation passed, stopping iteration")
                    break

                history.append(iteration_result)

            except Exception as e:
                logger.error(f"Execution error: {e}")
                history.append(IterationResult(
                    sql=current_sql,
                    success=False,
                    error=str(e),
                    suggestions="Fix the SQL syntax error and try again"
                ))

        return GenerationResult(
            sql=current_sql,
            results=current_results,
            iterations=len(history),
            history=history,
            satisfactory=satisfactory
        )

    def _build_prompt(
        self,
        question: str,
        schema: str,
        history: List[IterationResult]
    ) -> str:
        """Build prompt including history of previous attempts."""
        prompt = f"""### Instruction:
Generate a SQL query for the following question based on the given schema.

### Schema:
{schema}

### Question:
{question}
"""

        if history:
            prompt += "\n### Previous Attempts:\n"
            for i, attempt in enumerate(history, 1):
                prompt += f"\n--- Attempt {i} ---\n"
                prompt += f"SQL:\n{attempt.sql}\n"

                if not attempt.success:
                    prompt += f"Error: {attempt.error}\n"
                else:
                    prompt += f"Results Summary: {attempt.results_summary}\n"
                    if attempt.issues:
                        prompt += f"Issues: {attempt.issues}\n"
                    if attempt.suggestions:
                        prompt += f"Suggestions: {attempt.suggestions}\n"

            prompt += "\n### Generate improved SQL based on the feedback above:\n"
        else:
            prompt += "\n### SQL:\n"

        return prompt

    def _generate_sql(self, prompt: str) -> str:
        """Generate SQL using the local LLM."""
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.1,  # Low temperature for more deterministic output
            stop=["###", "\n\n\n"]
        )

        sql = response.strip()

        # Clean up the SQL
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        return sql.strip()

    def _execute_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return results."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)
        finally:
            cursor.close()

    def _summarize_results(self, results: pd.DataFrame) -> str:
        """Create a summary of the results for the LLM."""
        summary_parts = [
            f"Returned {len(results)} rows",
            f"Columns: {', '.join(results.columns)}"
        ]

        # Add sample data (first 5 rows)
        if len(results) > 0:
            sample = results.head(5).to_string(index=False)
            summary_parts.append(f"Sample data:\n{sample}")

        # Add basic statistics for numeric columns
        numeric_cols = results.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            stats = results[numeric_cols].describe().to_string()
            summary_parts.append(f"Statistics:\n{stats}")

        # Note null values
        null_counts = results.isnull().sum()
        if null_counts.any():
            null_info = null_counts[null_counts > 0].to_string()
            summary_parts.append(f"Null counts:\n{null_info}")

        return "\n".join(summary_parts)

    def _analyze_results(
        self,
        question: str,
        results: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Use the LLM to analyze if results answer the question.

        Since we're self-hosted, we can safely send full data to the LLM.
        """
        # Prepare results summary for analysis
        if len(results) == 0:
            results_text = "The query returned no results."
        elif len(results) > 10:
            results_text = f"First 10 rows of {len(results)} total:\n{results.head(10).to_string()}"
        else:
            results_text = results.to_string()

        analysis_prompt = f"""### Instruction:
Analyze if these SQL query results adequately answer the question.

### Question:
{question}

### Results:
{results_text}

### Analysis:
Evaluate the results and respond in JSON format:
{{
    "satisfactory": true or false,
    "issues": "description of any issues or empty string",
    "suggestions": "specific improvements or empty string"
}}

Consider:
1. Do the columns match what the question asks for?
2. Does the data make logical sense?
3. Are there any obvious issues (wrong aggregation, missing filters, etc.)?

### JSON Response:
"""

        response = self.llm.generate(
            prompt=analysis_prompt,
            max_tokens=500,
            temperature=0.1,
            stop=["###"]
        )

        try:
            # Parse JSON response
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            return json.loads(json_str)
        except json.JSONDecodeError:
            # If parsing fails, assume not satisfactory
            logger.warning(f"Could not parse analysis response: {response}")
            return {
                "satisfactory": False,
                "issues": "Could not analyze results",
                "suggestions": "Review the query manually"
            }


# Example usage
if __name__ == "__main__":
    # Example with vLLM client
    from vllm import LLM

    # Initialize local LLM
    llm = LLM(model="./mistral-7b-sql-lora")

    # Connect to Snowflake
    import snowflake.connector

    conn = snowflake.connector.connect(
        user="your_user",
        password="your_password",
        account="your_account",
        warehouse="your_warehouse",
        database="your_database",
        schema="your_schema"
    )

    # Create generator
    generator = IterativeSQLGenerator(
        llm_client=llm,
        snowflake_connection=conn,
        max_iterations=3
    )

    # Schema definition
    schema = """
    SALES(order_id INT, customer_id INT, product_id INT, quantity INT,
          unit_price DECIMAL(10,2), order_date DATE, region VARCHAR)
    CUSTOMERS(customer_id INT, name VARCHAR, email VARCHAR, segment VARCHAR)
    PRODUCTS(product_id INT, name VARCHAR, category VARCHAR, cost DECIMAL(10,2))
    """

    # Generate with refinement
    result = generator.generate_with_refinement(
        question="Find the top 10 customers by revenue in Q4 2024, including their segment",
        schema=schema
    )

    print(f"Final SQL:\n{result.sql}")
    print(f"\nIterations: {result.iterations}")
    print(f"Satisfactory: {result.satisfactory}")

    if result.results is not None:
        print(f"\nResults:\n{result.results}")
