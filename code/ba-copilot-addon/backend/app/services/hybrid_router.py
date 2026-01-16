"""
Hybrid LLM Router for BA Copilot

Routes queries to the optimal LLM backend based on data sensitivity,
complexity, location, and cost constraints.

Backends:
- Snowflake Cortex: For data in Snowflake needing full data access
- Self-hosted Mistral: For sensitive batch jobs with full data access
- Claude Haiku (API): For simple metadata-only queries (cheapest)
- Claude Sonnet (API): For moderate complexity, schema-only
- Claude Opus (API): For complex analysis (highest accuracy)
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSensitivity(Enum):
    """Data sensitivity levels."""
    PUBLIC = "public"           # Open data, no restrictions
    INTERNAL = "internal"       # Company internal, not PII
    CONFIDENTIAL = "confidential"  # PII, financial data
    RESTRICTED = "restricted"   # Regulated data (HIPAA, PCI)


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"       # Single table, basic aggregation
    MODERATE = "moderate"   # Joins, window functions
    COMPLEX = "complex"     # Multi-step analysis, iteration needed


class Backend(Enum):
    """Available LLM backends."""
    CORTEX = "cortex"
    MISTRAL = "mistral"
    CLAUDE_HAIKU = "claude_haiku"
    CLAUDE_SONNET = "claude_sonnet"
    CLAUDE_OPUS = "claude_opus"


@dataclass
class QueryContext:
    """Context for routing decisions."""
    question: str
    data_source: str  # 'snowflake', 'postgres', 'other'
    sensitivity: DataSensitivity
    complexity: QueryComplexity
    requires_iteration: bool
    estimated_tokens: int = 0
    user_preference: Optional[Backend] = None


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    backend: Backend
    reason: str
    estimated_cost: float
    data_exposure: str  # 'none', 'schema_only', 'aggregated', 'full'


class HybridRouter:
    """
    Routes queries to appropriate LLM backend based on context.

    The router evaluates multiple factors to select the optimal backend:
    1. Data sensitivity - Can data leave your infrastructure?
    2. Complexity - Does the query need a more capable model?
    3. Data location - Is data in Snowflake (Cortex available)?
    4. Iteration needs - Does refinement require data access?
    5. Cost constraints - What's the budget?
    """

    # Cost per 1000 tokens (approximate)
    COSTS = {
        Backend.CORTEX: 0.003,       # Snowflake credits
        Backend.MISTRAL: 0.001,      # Self-hosted (fixed cost amortized)
        Backend.CLAUDE_HAIKU: 0.0003,
        Backend.CLAUDE_SONNET: 0.003,
        Backend.CLAUDE_OPUS: 0.015,
    }

    def __init__(
        self,
        cortex_client=None,
        mistral_client=None,
        claude_client=None,
        enable_cortex: bool = True,
        enable_mistral: bool = True
    ):
        """
        Initialize the router with available clients.

        Args:
            cortex_client: Snowflake Cortex client
            mistral_client: Self-hosted Mistral client
            claude_client: Anthropic Claude client
            enable_cortex: Whether Cortex is available
            enable_mistral: Whether self-hosted Mistral is available
        """
        self.cortex = cortex_client
        self.mistral = mistral_client
        self.claude = claude_client

        self.enable_cortex = enable_cortex and cortex_client is not None
        self.enable_mistral = enable_mistral and mistral_client is not None

        logger.info(
            f"Router initialized - Cortex: {self.enable_cortex}, "
            f"Mistral: {self.enable_mistral}"
        )

    def route(self, context: QueryContext) -> RoutingDecision:
        """
        Determine which backend to use based on query context.

        Args:
            context: QueryContext with all relevant information

        Returns:
            RoutingDecision with backend choice and reasoning
        """
        # Honor user preference if valid
        if context.user_preference:
            if self._is_backend_available(context.user_preference):
                return RoutingDecision(
                    backend=context.user_preference,
                    reason="User preference",
                    estimated_cost=self._estimate_cost(
                        context.user_preference, context.estimated_tokens
                    ),
                    data_exposure=self._get_data_exposure(
                        context.user_preference, context.sensitivity
                    )
                )

        # Rule 1: Data in Snowflake + needs iteration = Cortex
        if (context.data_source == 'snowflake' and
            context.requires_iteration and
            self.enable_cortex):
            return RoutingDecision(
                backend=Backend.CORTEX,
                reason="Snowflake data with iteration - Cortex allows safe full data access",
                estimated_cost=self._estimate_cost(Backend.CORTEX, context.estimated_tokens),
                data_exposure="full"
            )

        # Rule 2: Sensitive data + needs iteration = Self-hosted only
        if context.sensitivity in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
            if context.requires_iteration:
                if self.enable_mistral:
                    return RoutingDecision(
                        backend=Backend.MISTRAL,
                        reason="Sensitive data requiring iteration - only self-hosted is safe",
                        estimated_cost=self._estimate_cost(Backend.MISTRAL, context.estimated_tokens),
                        data_exposure="full"
                    )
                elif self.enable_cortex and context.data_source == 'snowflake':
                    return RoutingDecision(
                        backend=Backend.CORTEX,
                        reason="Sensitive Snowflake data with iteration - Cortex is safe",
                        estimated_cost=self._estimate_cost(Backend.CORTEX, context.estimated_tokens),
                        data_exposure="full"
                    )
                else:
                    # Fallback to API with schema-only (limited accuracy)
                    logger.warning(
                        "Sensitive data needs iteration but no safe backend available. "
                        "Using schema-only with API (limited accuracy)."
                    )

            # Sensitive without iteration - can use API with schema only
            backend = (Backend.CLAUDE_SONNET if context.complexity == QueryComplexity.COMPLEX
                      else Backend.CLAUDE_HAIKU)
            return RoutingDecision(
                backend=backend,
                reason=f"Sensitive data, no iteration - schema-only API call",
                estimated_cost=self._estimate_cost(backend, context.estimated_tokens),
                data_exposure="schema_only"
            )

        # Rule 3: Simple queries = Cheapest option
        if context.complexity == QueryComplexity.SIMPLE:
            if context.data_source == 'snowflake' and self.enable_cortex:
                return RoutingDecision(
                    backend=Backend.CORTEX,
                    reason="Simple query in Snowflake - native Cortex is efficient",
                    estimated_cost=self._estimate_cost(Backend.CORTEX, context.estimated_tokens),
                    data_exposure="full"
                )
            return RoutingDecision(
                backend=Backend.CLAUDE_HAIKU,
                reason="Simple query - Haiku is fastest and cheapest",
                estimated_cost=self._estimate_cost(Backend.CLAUDE_HAIKU, context.estimated_tokens),
                data_exposure="schema_only"
            )

        # Rule 4: Complex analysis = Best model
        if context.complexity == QueryComplexity.COMPLEX:
            if context.data_source == 'snowflake' and self.enable_cortex:
                return RoutingDecision(
                    backend=Backend.CORTEX,
                    reason="Complex Snowflake analysis - Cortex with Claude for accuracy + data access",
                    estimated_cost=self._estimate_cost(Backend.CORTEX, context.estimated_tokens),
                    data_exposure="full"
                )
            return RoutingDecision(
                backend=Backend.CLAUDE_OPUS,
                reason="Complex analysis - Opus 4.5 for highest accuracy (95%+)",
                estimated_cost=self._estimate_cost(Backend.CLAUDE_OPUS, context.estimated_tokens),
                data_exposure="aggregated" if context.requires_iteration else "schema_only"
            )

        # Default: Balanced option
        return RoutingDecision(
            backend=Backend.CLAUDE_SONNET,
            reason="Default balanced option - good accuracy and cost",
            estimated_cost=self._estimate_cost(Backend.CLAUDE_SONNET, context.estimated_tokens),
            data_exposure="schema_only"
        )

    def execute(self, context: QueryContext) -> Dict[str, Any]:
        """
        Route and execute the query.

        Args:
            context: QueryContext with query information

        Returns:
            Dict with result, metadata, and routing info
        """
        # Get routing decision
        decision = self.route(context)
        logger.info(f"Routing to {decision.backend.value}: {decision.reason}")

        start_time = datetime.now()

        # Execute based on backend
        try:
            if decision.backend == Backend.CORTEX:
                result = self._execute_cortex(context, decision)
            elif decision.backend == Backend.MISTRAL:
                result = self._execute_mistral(context, decision)
            else:
                result = self._execute_claude(context, decision)

            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            return {
                "success": True,
                "result": result,
                "routing": {
                    "backend": decision.backend.value,
                    "reason": decision.reason,
                    "data_exposure": decision.data_exposure,
                    "estimated_cost": decision.estimated_cost
                },
                "latency_ms": latency_ms
            }

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "routing": {
                    "backend": decision.backend.value,
                    "reason": decision.reason
                }
            }

    def _execute_cortex(
        self,
        context: QueryContext,
        decision: RoutingDecision
    ) -> Dict[str, Any]:
        """Execute via Snowflake Cortex - full data access is safe."""
        if not self.cortex:
            raise RuntimeError("Cortex client not configured")

        # Can safely iterate with full data access
        return self.cortex.execute_with_iteration(
            question=context.question,
            max_iterations=3 if context.requires_iteration else 1
        )

    def _execute_mistral(
        self,
        context: QueryContext,
        decision: RoutingDecision
    ) -> Dict[str, Any]:
        """Execute via self-hosted Mistral - full data access is safe."""
        if not self.mistral:
            raise RuntimeError("Mistral client not configured")

        return self.mistral.generate_with_refinement(
            question=context.question,
            include_data=True  # Safe because self-hosted
        )

    def _execute_claude(
        self,
        context: QueryContext,
        decision: RoutingDecision
    ) -> Dict[str, Any]:
        """Execute via Claude API - careful with data exposure."""
        if not self.claude:
            raise RuntimeError("Claude client not configured")

        model_map = {
            Backend.CLAUDE_HAIKU: "claude-3-5-haiku-20241022",
            Backend.CLAUDE_SONNET: "claude-sonnet-4-20250514",
            Backend.CLAUDE_OPUS: "claude-opus-4-20250514",
        }

        return self.claude.generate(
            question=context.question,
            model=model_map[decision.backend],
            exposure_level=decision.data_exposure
        )

    def _is_backend_available(self, backend: Backend) -> bool:
        """Check if a backend is available."""
        if backend == Backend.CORTEX:
            return self.enable_cortex
        if backend == Backend.MISTRAL:
            return self.enable_mistral
        return self.claude is not None

    def _estimate_cost(self, backend: Backend, tokens: int) -> float:
        """Estimate cost for a query."""
        if tokens == 0:
            tokens = 1000  # Default estimate
        return (tokens / 1000) * self.COSTS[backend]

    def _get_data_exposure(
        self,
        backend: Backend,
        sensitivity: DataSensitivity
    ) -> str:
        """Determine data exposure level for backend + sensitivity combo."""
        # Self-hosted and Cortex are always safe for full access
        if backend in [Backend.CORTEX, Backend.MISTRAL]:
            return "full"

        # API with sensitive data = schema only
        if sensitivity in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
            return "schema_only"

        # API with internal data = aggregated
        if sensitivity == DataSensitivity.INTERNAL:
            return "aggregated"

        # Public data = full is okay
        return "full"


# Utility function for quick routing decisions
def quick_route(
    question: str,
    data_source: str = "snowflake",
    sensitivity: str = "internal",
    complexity: str = "moderate",
    needs_iteration: bool = False
) -> str:
    """
    Quick utility to get routing recommendation.

    Args:
        question: The query question
        data_source: 'snowflake', 'postgres', 'other'
        sensitivity: 'public', 'internal', 'confidential', 'restricted'
        complexity: 'simple', 'moderate', 'complex'
        needs_iteration: Whether iterative refinement is needed

    Returns:
        Recommended backend name
    """
    context = QueryContext(
        question=question,
        data_source=data_source,
        sensitivity=DataSensitivity(sensitivity),
        complexity=QueryComplexity(complexity),
        requires_iteration=needs_iteration
    )

    router = HybridRouter(enable_cortex=True, enable_mistral=True)
    decision = router.route(context)

    return decision.backend.value


# Example usage
if __name__ == "__main__":
    print("Hybrid Router - Routing Examples")
    print("=" * 60)

    # Create router (mock clients for demo)
    router = HybridRouter(
        cortex_client=None,  # Would be SnowflakeCortexClient
        mistral_client=None,  # Would be MistralClient
        claude_client=None,   # Would be AnthropicClient
        enable_cortex=True,
        enable_mistral=True
    )

    # Test scenarios
    scenarios = [
        QueryContext(
            question="Top 10 customers by revenue",
            data_source="snowflake",
            sensitivity=DataSensitivity.INTERNAL,
            complexity=QueryComplexity.SIMPLE,
            requires_iteration=False
        ),
        QueryContext(
            question="Analyze customer churn patterns",
            data_source="snowflake",
            sensitivity=DataSensitivity.CONFIDENTIAL,
            complexity=QueryComplexity.COMPLEX,
            requires_iteration=True
        ),
        QueryContext(
            question="Generate DAX for YoY growth",
            data_source="other",
            sensitivity=DataSensitivity.PUBLIC,
            complexity=QueryComplexity.MODERATE,
            requires_iteration=False
        ),
    ]

    for ctx in scenarios:
        decision = router.route(ctx)
        print(f"\nQuestion: {ctx.question}")
        print(f"  Source: {ctx.data_source}, Sensitivity: {ctx.sensitivity.value}")
        print(f"  → Backend: {decision.backend.value}")
        print(f"  → Reason: {decision.reason}")
        print(f"  → Data Exposure: {decision.data_exposure}")
        print(f"  → Est. Cost: ${decision.estimated_cost:.4f}")
