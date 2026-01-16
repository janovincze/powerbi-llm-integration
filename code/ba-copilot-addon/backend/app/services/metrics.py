"""
Hybrid Router Metrics and Monitoring

Track usage across all LLM backends for cost optimization,
quality monitoring, and usage analytics.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryMetric:
    """Metrics for a single query."""
    timestamp: datetime
    question: str
    sensitivity: str
    complexity: str
    backend: str
    success: bool
    iterations: int
    latency_ms: float
    estimated_cost: float
    actual_tokens: Optional[int] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time period."""
    total_queries: int
    successful_queries: int
    failed_queries: int
    total_cost: float
    avg_latency_ms: float
    queries_by_backend: Dict[str, int]
    queries_by_complexity: Dict[str, int]
    queries_by_sensitivity: Dict[str, int]
    avg_iterations: float


class HybridMetrics:
    """
    Track usage across all backends for cost and quality optimization.

    Features:
    - Real-time query logging
    - Cost tracking and forecasting
    - Performance monitoring
    - Optimization recommendations
    """

    def __init__(self, max_history: int = 10000):
        """
        Initialize metrics tracker.

        Args:
            max_history: Maximum queries to keep in memory
        """
        self.queries: List[QueryMetric] = []
        self.max_history = max_history

        # Real-time counters
        self._total_cost = 0.0
        self._query_count = 0
        self._success_count = 0

    def log_query(
        self,
        question: str,
        sensitivity: str,
        complexity: str,
        backend: str,
        success: bool,
        iterations: int,
        latency_ms: float,
        estimated_cost: float,
        actual_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> QueryMetric:
        """
        Log a query execution.

        Args:
            question: The natural language question
            sensitivity: Data sensitivity level
            complexity: Query complexity level
            backend: Backend used (cortex, mistral, claude_*)
            success: Whether execution succeeded
            iterations: Number of refinement iterations
            latency_ms: Total latency in milliseconds
            estimated_cost: Estimated cost in USD
            actual_tokens: Actual tokens used (if known)
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            The logged QueryMetric
        """
        metric = QueryMetric(
            timestamp=datetime.now(),
            question=question,
            sensitivity=sensitivity,
            complexity=complexity,
            backend=backend,
            success=success,
            iterations=iterations,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            actual_tokens=actual_tokens,
            user_id=user_id,
            session_id=session_id
        )

        self.queries.append(metric)
        self._query_count += 1
        self._total_cost += estimated_cost
        if success:
            self._success_count += 1

        # Trim history if needed
        if len(self.queries) > self.max_history:
            self.queries = self.queries[-self.max_history:]

        logger.debug(f"Logged query: {backend}, success={success}, cost=${estimated_cost:.4f}")

        return metric

    def get_aggregated_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> AggregatedMetrics:
        """
        Get aggregated metrics for a time period.

        Args:
            start_time: Start of period (None = beginning)
            end_time: End of period (None = now)

        Returns:
            AggregatedMetrics for the period
        """
        # Filter queries by time
        filtered = self.queries
        if start_time:
            filtered = [q for q in filtered if q.timestamp >= start_time]
        if end_time:
            filtered = [q for q in filtered if q.timestamp <= end_time]

        if not filtered:
            return AggregatedMetrics(
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                total_cost=0.0,
                avg_latency_ms=0.0,
                queries_by_backend={},
                queries_by_complexity={},
                queries_by_sensitivity={},
                avg_iterations=0.0
            )

        # Calculate aggregations
        total = len(filtered)
        successful = sum(1 for q in filtered if q.success)
        failed = total - successful
        total_cost = sum(q.estimated_cost for q in filtered)
        avg_latency = sum(q.latency_ms for q in filtered) / total
        avg_iterations = sum(q.iterations for q in filtered) / total

        # Group by dimensions
        by_backend = defaultdict(int)
        by_complexity = defaultdict(int)
        by_sensitivity = defaultdict(int)

        for q in filtered:
            by_backend[q.backend] += 1
            by_complexity[q.complexity] += 1
            by_sensitivity[q.sensitivity] += 1

        return AggregatedMetrics(
            total_queries=total,
            successful_queries=successful,
            failed_queries=failed,
            total_cost=total_cost,
            avg_latency_ms=avg_latency,
            queries_by_backend=dict(by_backend),
            queries_by_complexity=dict(by_complexity),
            queries_by_sensitivity=dict(by_sensitivity),
            avg_iterations=avg_iterations
        )

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """
        Analyze usage patterns and suggest optimizations.

        Returns:
            List of recommendation dicts with 'type', 'message', 'impact'
        """
        recommendations = []

        if len(self.queries) < 10:
            return [{"type": "info", "message": "Need more data for recommendations", "impact": "N/A"}]

        # Check if simple queries are using expensive backends
        simple_queries = [q for q in self.queries if q.complexity == 'simple']
        if simple_queries:
            expensive_simple = [q for q in simple_queries
                              if q.backend in ['claude_opus', 'claude_sonnet']]

            if len(expensive_simple) > len(simple_queries) * 0.3:
                potential_savings = sum(q.estimated_cost for q in expensive_simple) * 0.8
                recommendations.append({
                    "type": "cost_optimization",
                    "message": f"{len(expensive_simple)} simple queries ({len(expensive_simple)/len(simple_queries)*100:.0f}%) "
                              f"are using expensive models. Route to Haiku or Cortex to save ~80%.",
                    "impact": f"~${potential_savings:.2f} potential savings"
                })

        # Check if iteration-heavy queries use external APIs
        iterative_api = [q for q in self.queries
                        if q.iterations > 1 and 'claude' in q.backend]

        if iterative_api:
            recommendations.append({
                "type": "data_privacy",
                "message": f"{len(iterative_api)} queries required iteration with external API. "
                          "Consider Cortex or self-hosted for these to enable safe full data access "
                          "and improve accuracy.",
                "impact": "Better accuracy + data privacy"
            })

        # Check failure rate
        recent = self.queries[-100:] if len(self.queries) >= 100 else self.queries
        failure_rate = sum(1 for q in recent if not q.success) / len(recent)

        if failure_rate > 0.1:
            recommendations.append({
                "type": "reliability",
                "message": f"Failure rate is {failure_rate*100:.1f}% (last {len(recent)} queries). "
                          "Review error patterns and consider adding retries or fallbacks.",
                "impact": "Improved reliability"
            })

        # Check latency
        avg_latency = sum(q.latency_ms for q in recent) / len(recent)
        if avg_latency > 5000:  # 5 seconds
            slow_backends = defaultdict(list)
            for q in recent:
                if q.latency_ms > 5000:
                    slow_backends[q.backend].append(q.latency_ms)

            slowest = max(slow_backends.items(), key=lambda x: sum(x[1])/len(x[1]))
            recommendations.append({
                "type": "performance",
                "message": f"Average latency is {avg_latency/1000:.1f}s. "
                          f"{slowest[0]} is slowest with avg {sum(slowest[1])/len(slowest[1])/1000:.1f}s. "
                          "Consider caching or using faster models for common queries.",
                "impact": "Better user experience"
            })

        # Check cost distribution
        if self._total_cost > 0:
            cost_by_backend = defaultdict(float)
            for q in self.queries:
                cost_by_backend[q.backend] += q.estimated_cost

            top_cost_backend = max(cost_by_backend.items(), key=lambda x: x[1])
            if top_cost_backend[1] > self._total_cost * 0.7:
                recommendations.append({
                    "type": "cost_distribution",
                    "message": f"{top_cost_backend[0]} accounts for {top_cost_backend[1]/self._total_cost*100:.0f}% "
                              f"of total cost (${top_cost_backend[1]:.2f}). "
                              "Consider load balancing or using cheaper alternatives for some queries.",
                    "impact": "Cost optimization opportunity"
                })

        if not recommendations:
            recommendations.append({
                "type": "info",
                "message": "No optimization opportunities identified. Current routing is efficient.",
                "impact": "N/A"
            })

        return recommendations

    def get_cost_forecast(self, days: int = 30) -> Dict[str, Any]:
        """
        Forecast costs based on current usage patterns.

        Args:
            days: Number of days to forecast

        Returns:
            Dict with forecast details
        """
        if not self.queries:
            return {"error": "No data for forecasting"}

        # Calculate daily rate from recent data
        recent = self.queries[-1000:] if len(self.queries) >= 1000 else self.queries

        if len(recent) < 2:
            return {"error": "Insufficient data for forecasting"}

        time_span = (recent[-1].timestamp - recent[0].timestamp).total_seconds() / 86400
        if time_span < 0.1:
            time_span = 1.0  # Assume at least 1 day if very recent

        daily_queries = len(recent) / time_span
        daily_cost = sum(q.estimated_cost for q in recent) / time_span

        return {
            "forecast_period_days": days,
            "projected_queries": int(daily_queries * days),
            "projected_cost": daily_cost * days,
            "daily_query_rate": daily_queries,
            "daily_cost_rate": daily_cost,
            "cost_by_backend": {
                backend: sum(q.estimated_cost for q in recent if q.backend == backend) / time_span * days
                for backend in set(q.backend for q in recent)
            }
        }

    def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics data.

        Args:
            format: 'json' or 'csv'

        Returns:
            Formatted string
        """
        if format == "json":
            return json.dumps([
                {
                    "timestamp": q.timestamp.isoformat(),
                    "question": q.question[:50] + "..." if len(q.question) > 50 else q.question,
                    "backend": q.backend,
                    "success": q.success,
                    "iterations": q.iterations,
                    "latency_ms": q.latency_ms,
                    "cost": q.estimated_cost
                }
                for q in self.queries
            ], indent=2)

        elif format == "csv":
            lines = ["timestamp,backend,success,iterations,latency_ms,cost"]
            for q in self.queries:
                lines.append(f"{q.timestamp.isoformat()},{q.backend},{q.success},"
                           f"{q.iterations},{q.latency_ms:.1f},{q.estimated_cost:.6f}")
            return "\n".join(lines)

        else:
            raise ValueError(f"Unknown format: {format}")


# Example usage
if __name__ == "__main__":
    import random

    print("Hybrid Metrics - Demo")
    print("=" * 60)

    # Create metrics tracker
    metrics = HybridMetrics()

    # Simulate some queries
    backends = ["cortex", "mistral", "claude_haiku", "claude_sonnet", "claude_opus"]
    complexities = ["simple", "moderate", "complex"]
    sensitivities = ["public", "internal", "confidential"]

    for i in range(100):
        backend = random.choice(backends)
        metrics.log_query(
            question=f"Sample query {i}",
            sensitivity=random.choice(sensitivities),
            complexity=random.choice(complexities),
            backend=backend,
            success=random.random() > 0.1,  # 90% success rate
            iterations=random.randint(1, 3),
            latency_ms=random.uniform(500, 8000),
            estimated_cost=random.uniform(0.001, 0.05)
        )

    # Show aggregated metrics
    agg = metrics.get_aggregated_metrics()
    print(f"\nAggregated Metrics:")
    print(f"  Total queries: {agg.total_queries}")
    print(f"  Success rate: {agg.successful_queries/agg.total_queries*100:.1f}%")
    print(f"  Total cost: ${agg.total_cost:.2f}")
    print(f"  Avg latency: {agg.avg_latency_ms:.0f}ms")
    print(f"  Queries by backend: {agg.queries_by_backend}")

    # Show recommendations
    print(f"\nRecommendations:")
    for rec in metrics.get_recommendations():
        print(f"  [{rec['type']}] {rec['message']}")
        print(f"    Impact: {rec['impact']}")

    # Show forecast
    print(f"\nCost Forecast (30 days):")
    forecast = metrics.get_cost_forecast(30)
    print(f"  Projected queries: {forecast['projected_queries']}")
    print(f"  Projected cost: ${forecast['projected_cost']:.2f}")
