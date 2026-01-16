"""
Safe Iterative SQL Generator with Configurable Data Exposure

This module provides iterative SQL refinement with configurable data exposure
levels, allowing you to balance accuracy improvements against privacy requirements.

Exposure Levels:
- schema_only: Only structural metadata (row count, columns, types) - SAFEST
- aggregated: Aggregated statistics (min, max, mean, etc.) - MODERATE
- full: Complete result data - FULL ACCURACY (use only with self-hosted/Cortex)
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExposureLevel(Enum):
    """Data exposure levels for iterative refinement."""
    SCHEMA_ONLY = "schema_only"
    AGGREGATED = "aggregated"
    FULL = "full"


@dataclass
class FeedbackData:
    """Structured feedback data sent to LLM."""
    row_count: int
    columns: List[str]
    column_types: Dict[str, str]
    numeric_stats: Optional[Dict] = None
    null_counts: Optional[Dict] = None
    sample_data: Optional[List[Dict]] = None
    full_stats: Optional[Dict] = None


@dataclass
class IterationHistory:
    """Record of a single iteration."""
    iteration: int
    sql: str
    success: bool
    feedback: Optional[FeedbackData] = None
    error: Optional[str] = None
    analysis: Optional[Dict] = None


class SafeIterativeGenerator:
    """
    Iterative SQL refinement with configurable data exposure levels.

    This class allows you to control how much data is shared with the LLM
    during the refinement process:

    - SCHEMA_ONLY: Safe for any API (only metadata shared)
    - AGGREGATED: Usually safe (statistical summaries only)
    - FULL: Maximum accuracy (requires self-hosted or Cortex)

    Example:
        ```python
        # For external API with sensitive data
        generator = SafeIterativeGenerator(llm, db, ExposureLevel.SCHEMA_ONLY)

        # For self-hosted LLM (full data is safe)
        generator = SafeIterativeGenerator(llm, db, ExposureLevel.FULL)
        ```
    """

    def __init__(
        self,
        llm_client,
        db_executor,
        exposure_level: ExposureLevel = ExposureLevel.SCHEMA_ONLY,
        max_iterations: int = 3
    ):
        """
        Initialize the safe generator.

        Args:
            llm_client: LLM client with generate() method
            db_executor: Database executor with run() method returning DataFrame
            exposure_level: How much data to share with LLM
            max_iterations: Maximum refinement attempts
        """
        self.llm = llm_client
        self.executor = db_executor
        self.exposure_level = exposure_level
        self.max_iterations = max_iterations

        logger.info(f"Initialized with exposure level: {exposure_level.value}")
        if exposure_level == ExposureLevel.FULL:
            logger.warning(
                "FULL exposure level selected. Only use with self-hosted LLM or Cortex!"
            )

    def generate(
        self,
        question: str,
        schema: str
    ) -> Dict[str, Any]:
        """
        Generate SQL with iterative refinement.

        Args:
            question: Natural language question
            schema: Database schema description

        Returns:
            Dict with 'sql', 'results', 'iterations', 'history', 'satisfactory'
        """
        history: List[IterationHistory] = []
        current_sql = ""
        current_results = None
        satisfactory = False

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Iteration {iteration}/{self.max_iterations}")

            # Generate SQL
            prompt = self._build_prompt(question, schema, history)
            current_sql = self._generate_sql(prompt)

            # Execute
            try:
                current_results = self.executor.run(current_sql)
                logger.info(f"Query returned {len(current_results)} rows")

                # Prepare feedback based on exposure level
                feedback = self._prepare_feedback(current_results)

                # Analyze results
                analysis = self._analyze_results(question, feedback)

                history.append(IterationHistory(
                    iteration=iteration,
                    sql=current_sql,
                    success=True,
                    feedback=feedback,
                    analysis=analysis
                ))

                # Check if satisfactory
                if analysis.get("satisfactory", False):
                    satisfactory = True
                    logger.info("Results satisfactory, stopping")
                    break

            except Exception as e:
                logger.error(f"Execution failed: {e}")
                history.append(IterationHistory(
                    iteration=iteration,
                    sql=current_sql,
                    success=False,
                    error=str(e)
                ))

        return {
            "sql": current_sql,
            "results": current_results,
            "iterations": len(history),
            "history": history,
            "satisfactory": satisfactory,
            "exposure_level": self.exposure_level.value
        }

    def _prepare_feedback(self, results: pd.DataFrame) -> FeedbackData:
        """
        Prepare feedback data based on exposure level.

        This is the key method that controls data privacy.
        """
        base_feedback = FeedbackData(
            row_count=len(results),
            columns=list(results.columns),
            column_types={col: str(dtype) for col, dtype in results.dtypes.items()}
        )

        if self.exposure_level == ExposureLevel.SCHEMA_ONLY:
            # Only structural information - SAFEST
            logger.debug("Using SCHEMA_ONLY feedback")
            return base_feedback

        elif self.exposure_level == ExposureLevel.AGGREGATED:
            # Add aggregated statistics - MODERATE RISK
            logger.debug("Using AGGREGATED feedback")
            base_feedback.null_counts = results.isnull().sum().to_dict()

            numeric_cols = results.select_dtypes(include=['number'])
            if not numeric_cols.empty:
                base_feedback.numeric_stats = {
                    col: {
                        "min": float(numeric_cols[col].min()),
                        "max": float(numeric_cols[col].max()),
                        "mean": float(numeric_cols[col].mean()),
                        "std": float(numeric_cols[col].std()),
                        "median": float(numeric_cols[col].median())
                    }
                    for col in numeric_cols.columns
                }

            return base_feedback

        else:  # FULL exposure
            # Full data access - USE ONLY WITH SELF-HOSTED/CORTEX
            logger.debug("Using FULL feedback (ensure LLM is self-hosted!)")
            base_feedback.null_counts = results.isnull().sum().to_dict()
            base_feedback.sample_data = results.head(10).to_dict(orient="records")

            if not results.empty:
                base_feedback.full_stats = results.describe().to_dict()

            return base_feedback

    def _build_prompt(
        self,
        question: str,
        schema: str,
        history: List[IterationHistory]
    ) -> str:
        """Build generation prompt with history."""
        prompt = f"""Generate a SQL query for this question.

Schema:
{schema}

Question: {question}
"""

        if history:
            prompt += "\n\nPrevious Attempts:\n"
            for h in history:
                prompt += f"\n--- Attempt {h.iteration} ---\n"
                prompt += f"SQL: {h.sql}\n"

                if h.success and h.feedback:
                    prompt += f"Result: {h.feedback.row_count} rows, "
                    prompt += f"columns: {', '.join(h.feedback.columns)}\n"

                    if h.analysis:
                        if h.analysis.get("issues"):
                            prompt += f"Issues: {h.analysis['issues']}\n"
                        if h.analysis.get("suggestions"):
                            prompt += f"Suggestions: {h.analysis['suggestions']}\n"
                else:
                    prompt += f"Error: {h.error}\n"

            prompt += "\nGenerate improved SQL:\n"
        else:
            prompt += "\nSQL:\n"

        return prompt

    def _generate_sql(self, prompt: str) -> str:
        """Generate SQL from prompt."""
        response = self.llm.generate(prompt)

        # Clean markdown if present
        sql = response.strip()
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0]
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0]

        return sql.strip()

    def _analyze_results(
        self,
        question: str,
        feedback: FeedbackData
    ) -> Dict[str, Any]:
        """Analyze if results are satisfactory."""
        # Convert feedback to JSON-serializable dict
        feedback_dict = {
            "row_count": feedback.row_count,
            "columns": feedback.columns,
            "column_types": feedback.column_types
        }

        if feedback.null_counts:
            feedback_dict["null_counts"] = feedback.null_counts
        if feedback.numeric_stats:
            feedback_dict["numeric_stats"] = feedback.numeric_stats
        if feedback.sample_data:
            feedback_dict["sample_data"] = feedback.sample_data

        analysis_prompt = f"""Analyze if these query results answer the question.

Question: {question}

Results Metadata:
{json.dumps(feedback_dict, indent=2, default=str)}

Respond in JSON:
{{"satisfactory": true/false, "issues": "...", "suggestions": "..."}}"""

        response = self.llm.generate(analysis_prompt)

        try:
            # Extract JSON from response
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {"satisfactory": False, "issues": "Could not parse analysis"}

    @staticmethod
    def recommend_exposure_level(
        data_sensitivity: str,
        llm_location: str,
        iteration_needed: bool
    ) -> ExposureLevel:
        """
        Recommend appropriate exposure level based on context.

        Args:
            data_sensitivity: 'public', 'internal', 'confidential', 'restricted'
            llm_location: 'self_hosted', 'cortex', 'external_api'
            iteration_needed: Whether iterative refinement is required

        Returns:
            Recommended ExposureLevel
        """
        # Self-hosted or Cortex: full access is safe
        if llm_location in ("self_hosted", "cortex"):
            return ExposureLevel.FULL

        # External API with sensitive data
        if data_sensitivity in ("confidential", "restricted"):
            if iteration_needed:
                logger.warning(
                    "Sensitive data with iteration needed - consider self-hosted/Cortex"
                )
            return ExposureLevel.SCHEMA_ONLY

        # External API with internal data
        if data_sensitivity == "internal":
            return ExposureLevel.AGGREGATED

        # Public data - safe for full exposure
        return ExposureLevel.FULL


# Example usage and comparison
if __name__ == "__main__":
    print("Safe Iterative Generator - Exposure Level Comparison")
    print("=" * 60)

    # Mock LLM and executor for demonstration
    class MockLLM:
        def generate(self, prompt):
            return "SELECT * FROM sales LIMIT 10"

    class MockExecutor:
        def run(self, sql):
            return pd.DataFrame({
                "customer_id": [1, 2, 3],
                "revenue": [100.50, 200.75, 150.25],
                "region": ["North", "South", "East"]
            })

    llm = MockLLM()
    executor = MockExecutor()

    # Compare exposure levels
    for level in ExposureLevel:
        print(f"\n{level.value.upper()} Exposure:")
        print("-" * 40)

        gen = SafeIterativeGenerator(llm, executor, level, max_iterations=1)
        result = gen.generate(
            "Top customers by revenue",
            "SALES(customer_id, revenue, region)"
        )

        feedback = result["history"][0].feedback
        print(f"  Row count: {feedback.row_count}")
        print(f"  Columns: {feedback.columns}")
        print(f"  Numeric stats: {feedback.numeric_stats is not None}")
        print(f"  Sample data: {feedback.sample_data is not None}")

    # Recommendation example
    print("\n" + "=" * 60)
    print("Exposure Level Recommendations:")
    print("-" * 40)

    scenarios = [
        ("confidential", "external_api", True),
        ("internal", "external_api", False),
        ("public", "external_api", True),
        ("confidential", "self_hosted", True),
        ("confidential", "cortex", True),
    ]

    for sensitivity, location, needs_iteration in scenarios:
        rec = SafeIterativeGenerator.recommend_exposure_level(
            sensitivity, location, needs_iteration
        )
        print(f"  {sensitivity} + {location}: {rec.value}")
