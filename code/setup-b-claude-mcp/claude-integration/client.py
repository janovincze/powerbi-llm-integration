"""
Claude API client with MCP tool integration.
Provides a high-level interface for data analytics workflows.
"""

import os
from typing import Optional
import anthropic


class ClaudeDataAssistant:
    """Claude-powered assistant for data analytics tasks."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
    ):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.conversation_history = []
        self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return """You are a data analytics assistant specializing in:
- SQL query generation for Snowflake
- DAX measure creation for PowerBI
- Data analysis and interpretation
- Business intelligence best practices

When generating code:
1. Use clear, readable formatting
2. Add comments explaining complex logic
3. Follow best practices for the target platform
4. Consider performance implications

When analyzing data:
1. Look for patterns and anomalies
2. Provide actionable insights
3. Suggest follow-up questions
4. Cite specific data points"""

    def set_context(self, schema_info: str, business_context: str = ""):
        """Set context for the conversation."""
        self.system_prompt = f"""{self._default_system_prompt()}

Available Schema:
{schema_info}

Business Context:
{business_context}"""

    def chat(
        self,
        message: str,
        use_extended_thinking: bool = False,
    ) -> str:
        """
        Send a message and get a response.

        Args:
            message: User message
            use_extended_thinking: Enable extended thinking for complex tasks

        Returns:
            Assistant response
        """
        self.conversation_history.append({
            "role": "user",
            "content": message,
        })

        params = {
            "model": self.model,
            "max_tokens": 4096,
            "system": self.system_prompt,
            "messages": self.conversation_history,
        }

        if use_extended_thinking:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": 10000,
            }

        response = self.client.messages.create(**params)

        assistant_message = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message,
        })

        return assistant_message

    def generate_sql(
        self,
        question: str,
        schema_context: str,
        dialect: str = "snowflake",
    ) -> dict:
        """
        Generate SQL from natural language.

        Args:
            question: Natural language question
            schema_context: Schema information
            dialect: SQL dialect (snowflake, postgres, etc.)

        Returns:
            Dict with sql, explanation, and token usage
        """
        prompt = f"""Generate a {dialect.upper()} SQL query to answer this question:

Question: {question}

Available Schema:
{schema_context}

Requirements:
- Use explicit JOIN syntax
- Qualify column names with table aliases
- Add comments for complex logic
- Optimize for performance

Provide:
1. The SQL query
2. A brief explanation of the query logic
3. Any assumptions made"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "response": response.content[0].text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

    def generate_dax(
        self,
        question: str,
        model_context: str,
    ) -> dict:
        """
        Generate DAX measure from natural language.

        Args:
            question: What the measure should calculate
            model_context: PowerBI semantic model context

        Returns:
            Dict with dax, explanation, and token usage
        """
        prompt = f"""Generate a DAX measure for this requirement:

Requirement: {question}

Semantic Model:
{model_context}

Best Practices:
- Use variables for clarity
- Avoid nested CALCULATE when possible
- Add comments for complex logic
- Consider filter context

Provide:
1. The DAX measure definition
2. An explanation of how it works
3. Example usage scenarios"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "response": response.content[0].text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

    def analyze_data(
        self,
        data_summary: str,
        question: str,
    ) -> str:
        """
        Analyze data and provide insights.

        Args:
            data_summary: Summary of the data to analyze
            question: Specific question or general analysis request

        Returns:
            Analysis with insights and recommendations
        """
        prompt = f"""Analyze this data and provide insights:

Data Summary:
{data_summary}

Question/Focus: {question}

Please provide:
1. Key observations
2. Notable patterns or anomalies
3. Actionable recommendations
4. Suggested follow-up analyses"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


def main():
    """Example usage."""
    assistant = ClaudeDataAssistant()

    # Set context
    schema = """
    Tables:
    - sales (id, date, customer_id, product_id, amount, region)
    - customers (id, name, segment, created_at)
    - products (id, name, category, price)
    """

    assistant.set_context(schema, "E-commerce analytics")

    # Generate SQL
    result = assistant.generate_sql(
        "What are the top 10 customers by total sales in 2024?",
        schema,
    )
    print("SQL Generation:")
    print(result["response"])
    print(f"\nTokens: {result['input_tokens']} in, {result['output_tokens']} out")

    # Interactive chat
    print("\n" + "=" * 50)
    print("Starting interactive chat (type 'quit' to exit)")
    print("=" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == "quit":
            break

        response = assistant.chat(user_input)
        print(f"\nAssistant: {response}")


if __name__ == "__main__":
    main()
