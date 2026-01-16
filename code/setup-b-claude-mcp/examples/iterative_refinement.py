"""
Iterative SQL Refinement with Claude API

This example demonstrates how to use Claude API for iterative query refinement.
Note: When using external APIs, be careful about what data you send.

Data Privacy Considerations:
- Iteration 1: Schema only - DATA STAYS LOCAL
- Iteration 2+: If you send results - DATA LEAVES your infrastructure
- For sensitive data, use self-hosted or Snowflake Cortex instead
"""

import anthropic
import json
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class RefinementResult:
    """Result of an iterative refinement session."""
    sql: str
    iterations: int
    history: list
    final_explanation: str


class ClaudeIterativeRefiner:
    """
    Iterative SQL generator using Claude API.

    IMPORTANT: This class can be configured for different data exposure levels:
    - schema_only: Only schema metadata sent (safe for sensitive data)
    - aggregated: Aggregated statistics sent (usually safe)
    - full: Full result data sent (only use for non-sensitive data)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        exposure_level: str = "schema_only"
    ):
        """
        Initialize the refiner.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use
            exposure_level: One of 'schema_only', 'aggregated', 'full'
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.exposure_level = exposure_level

    def generate_sql(
        self,
        question: str,
        schema: str,
        execute_fn: callable,
        max_iterations: int = 3
    ) -> RefinementResult:
        """
        Generate SQL with iterative refinement.

        Args:
            question: Natural language question
            schema: Database schema description
            execute_fn: Function that executes SQL and returns DataFrame
            max_iterations: Maximum refinement iterations

        Returns:
            RefinementResult with final SQL and history
        """
        history = []
        current_sql = ""

        for iteration in range(1, max_iterations + 1):
            # Build prompt based on iteration
            if iteration == 1:
                prompt = self._build_initial_prompt(question, schema)
            else:
                prompt = self._build_refinement_prompt(
                    question, schema, history
                )

            # Generate SQL
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            current_sql = self._extract_sql(response.content[0].text)

            # Try to execute
            try:
                results = execute_fn(current_sql)
                feedback = self._analyze_results(question, results)

                history.append({
                    "iteration": iteration,
                    "sql": current_sql,
                    "success": True,
                    "feedback": feedback
                })

                # Check if satisfactory
                if feedback.get("satisfactory", False):
                    break

            except Exception as e:
                history.append({
                    "iteration": iteration,
                    "sql": current_sql,
                    "success": False,
                    "error": str(e)
                })

        # Generate final explanation
        explanation = self._generate_explanation(question, current_sql)

        return RefinementResult(
            sql=current_sql,
            iterations=len(history),
            history=history,
            final_explanation=explanation
        )

    def _build_initial_prompt(self, question: str, schema: str) -> str:
        """Build prompt for initial SQL generation."""
        return f"""Generate a SQL query for the following question.

Schema:
{schema}

Question: {question}

Requirements:
- Use standard SQL syntax
- Include appropriate JOINs if multiple tables are needed
- Add comments explaining the logic
- Return only the SQL query, no additional explanation

SQL:"""

    def _build_refinement_prompt(
        self,
        question: str,
        schema: str,
        history: list
    ) -> str:
        """Build prompt for refinement based on previous attempts."""
        prompt = f"""Improve the SQL query based on previous feedback.

Schema:
{schema}

Question: {question}

Previous Attempts:
"""
        for entry in history:
            prompt += f"\n--- Attempt {entry['iteration']} ---\n"
            prompt += f"SQL: {entry['sql']}\n"

            if entry.get("success"):
                prompt += f"Feedback: {json.dumps(entry['feedback'])}\n"
            else:
                prompt += f"Error: {entry['error']}\n"

        prompt += """
Please generate an improved SQL query that addresses the feedback.
Return only the SQL query."""

        return prompt

    def _analyze_results(
        self,
        question: str,
        results: pd.DataFrame
    ) -> dict:
        """
        Analyze query results based on exposure level.

        This is where data privacy matters most!
        """
        if self.exposure_level == "schema_only":
            # Only send structural information - SAFE
            feedback_data = {
                "row_count": len(results),
                "columns": list(results.columns),
                "column_types": {col: str(dtype) for col, dtype in results.dtypes.items()}
            }
        elif self.exposure_level == "aggregated":
            # Send aggregated statistics - USUALLY SAFE
            feedback_data = {
                "row_count": len(results),
                "columns": list(results.columns),
                "numeric_stats": results.describe().to_dict() if not results.empty else {},
                "null_counts": results.isnull().sum().to_dict()
            }
        else:
            # Send full data - USE WITH CAUTION
            # Only appropriate for non-sensitive data
            feedback_data = {
                "row_count": len(results),
                "columns": list(results.columns),
                "sample_data": results.head(5).to_dict(orient="records"),
                "stats": results.describe().to_dict() if not results.empty else {}
            }

        # Ask Claude to analyze the results
        analysis_prompt = f"""Analyze if these query results answer the question.

Question: {question}

Result Metadata:
{json.dumps(feedback_data, indent=2, default=str)}

Determine:
1. Do the results appear to answer the question? (true/false)
2. Are there any obvious issues?
3. What improvements would help?

Respond in JSON format:
{{"satisfactory": true/false, "issues": "...", "suggestions": "..."}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": analysis_prompt}]
        )

        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            return {"satisfactory": True, "issues": "Could not parse analysis"}

    def _extract_sql(self, text: str) -> str:
        """Extract SQL from response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        if "```sql" in text:
            start = text.find("```sql") + 6
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        return text.strip()

    def _generate_explanation(self, question: str, sql: str) -> str:
        """Generate a natural language explanation of the final SQL."""
        prompt = f"""Explain this SQL query in plain English for a business analyst.

Question: {question}

SQL:
{sql}

Provide a clear, concise explanation."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


# Example usage
if __name__ == "__main__":
    import snowflake.connector

    # Example: Connect to Snowflake
    def get_snowflake_connection():
        return snowflake.connector.connect(
            user="your_user",
            password="your_password",
            account="your_account",
            warehouse="your_warehouse",
            database="your_database",
            schema="your_schema"
        )

    # Example execution function
    def execute_query(sql: str) -> pd.DataFrame:
        conn = get_snowflake_connection()
        try:
            return pd.read_sql(sql, conn)
        finally:
            conn.close()

    # Schema definition
    schema = """
    CUSTOMERS(customer_id INT PK, name VARCHAR, email VARCHAR, segment VARCHAR, created_at TIMESTAMP)
    ORDERS(order_id INT PK, customer_id INT FK, order_date DATE, total_amount DECIMAL, status VARCHAR)
    ORDER_ITEMS(item_id INT PK, order_id INT FK, product_id INT, quantity INT, unit_price DECIMAL)
    PRODUCTS(product_id INT PK, name VARCHAR, category VARCHAR, cost DECIMAL)
    """

    # Initialize refiner with schema-only exposure (safe for sensitive data)
    refiner = ClaudeIterativeRefiner(
        model="claude-sonnet-4-20250514",
        exposure_level="schema_only"  # Change to "aggregated" or "full" for more feedback
    )

    # Generate SQL
    result = refiner.generate_sql(
        question="Find customers who have placed more than 5 orders in the last 90 days with their total spend",
        schema=schema,
        execute_fn=execute_query,
        max_iterations=3
    )

    print("Final SQL:")
    print(result.sql)
    print(f"\nIterations: {result.iterations}")
    print(f"\nExplanation: {result.final_explanation}")
