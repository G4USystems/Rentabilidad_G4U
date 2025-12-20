"""Abstract LLM provider interface for scenario simulation."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_scenario(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a scenario based on the prompts and context.

        Args:
            system_prompt: Instructions for the LLM
            user_prompt: User's scenario request
            context: Historical data and metrics

        Returns:
            Dictionary with scenario assumptions and projections
        """
        pass


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider for testing.

    Generates reasonable scenarios based on historical data patterns.
    """

    async def generate_scenario(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a mock scenario based on context."""
        # Extract historical metrics
        historical = context.get("historical_metrics", {})
        avg_revenue = float(historical.get("avg_monthly_revenue", 10000))
        avg_expenses = float(historical.get("avg_monthly_expenses", 8000))
        avg_clients = int(historical.get("avg_active_clients", 5))

        # Parse user prompt for hints
        prompt_lower = user_prompt.lower()

        # Default assumptions
        revenue_growth = 0.05  # 5% growth
        expense_growth = 0.03  # 3% growth
        new_clients = 1
        churn_rate = 0.1  # 10% churn

        # Adjust based on user prompt keywords
        if "optimistic" in prompt_lower or "growth" in prompt_lower or "best" in prompt_lower:
            revenue_growth = 0.15
            expense_growth = 0.05
            new_clients = 3
            churn_rate = 0.05
        elif "pessimistic" in prompt_lower or "worst" in prompt_lower or "crisis" in prompt_lower:
            revenue_growth = -0.10
            expense_growth = 0.08
            new_clients = 0
            churn_rate = 0.25
        elif "hire" in prompt_lower or "contrat" in prompt_lower:
            expense_growth = 0.15
            revenue_growth = 0.10
        elif "reduce" in prompt_lower or "cut" in prompt_lower:
            expense_growth = -0.10
            revenue_growth = 0.02

        # Project 6 months
        projections = []
        current_revenue = avg_revenue
        current_expenses = avg_expenses
        current_clients = avg_clients

        for month in range(1, 7):
            current_revenue *= (1 + revenue_growth / 12)
            current_expenses *= (1 + expense_growth / 12)
            current_clients = max(1, int(current_clients * (1 - churn_rate / 12) + new_clients / 12))

            projections.append({
                "month": month,
                "projected_revenue": round(current_revenue, 2),
                "projected_expenses": round(current_expenses, 2),
                "projected_profit": round(current_revenue - current_expenses, 2),
                "projected_clients": current_clients,
            })

        return {
            "scenario_name": f"Scenario based on: {user_prompt[:50]}...",
            "assumptions": {
                "revenue_growth_rate": revenue_growth,
                "expense_growth_rate": expense_growth,
                "new_clients_per_month": new_clients,
                "churn_rate": churn_rate,
                "base_revenue": avg_revenue,
                "base_expenses": avg_expenses,
            },
            "projections": projections,
            "summary": {
                "total_projected_revenue": sum(p["projected_revenue"] for p in projections),
                "total_projected_expenses": sum(p["projected_expenses"] for p in projections),
                "total_projected_profit": sum(p["projected_profit"] for p in projections),
                "final_client_count": projections[-1]["projected_clients"] if projections else current_clients,
            },
            "reasoning": f"Based on your prompt '{user_prompt[:100]}', I've modeled a scenario with "
                        f"{revenue_growth*100:.1f}% revenue growth and {expense_growth*100:.1f}% expense growth.",
            "provider": "mock",
        }


class OpenAIProvider(LLMProvider):
    """OpenAI-based LLM provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    async def generate_scenario(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate scenario using OpenAI."""
        if not self.api_key:
            logger.warning("OpenAI API key not configured, falling back to mock provider")
            mock = MockLLMProvider()
            return await mock.generate_scenario(system_prompt, user_prompt, context)

        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)

            # Build the full prompt with context
            context_str = json.dumps(context, indent=2, default=str)
            full_user_prompt = f"""
Context (Historical Data):
{context_str}

User Request:
{user_prompt}

Please respond with a JSON object containing:
- scenario_name: A descriptive name for this scenario
- assumptions: Object with key assumptions (rates, growth factors, etc.)
- projections: Array of 6 monthly projections with projected_revenue, projected_expenses, projected_profit
- summary: Object with totals (total_projected_revenue, total_projected_expenses, total_projected_profit)
- reasoning: Brief explanation of your projections
"""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            result = json.loads(response.choices[0].message.content)
            result["provider"] = "openai"
            return result

        except Exception as e:
            logger.error(f"OpenAI API error: {e}, falling back to mock")
            mock = MockLLMProvider()
            result = await mock.generate_scenario(system_prompt, user_prompt, context)
            result["error"] = str(e)
            return result


class AnthropicProvider(LLMProvider):
    """Anthropic Claude-based LLM provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        import os
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    async def generate_scenario(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate scenario using Anthropic Claude."""
        if not self.api_key:
            logger.warning("Anthropic API key not configured, falling back to mock provider")
            mock = MockLLMProvider()
            return await mock.generate_scenario(system_prompt, user_prompt, context)

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)

            context_str = json.dumps(context, indent=2, default=str)
            full_user_prompt = f"""
Context (Historical Data):
{context_str}

User Request:
{user_prompt}

Please respond with a JSON object containing:
- scenario_name: A descriptive name for this scenario
- assumptions: Object with key assumptions (rates, growth factors, etc.)
- projections: Array of 6 monthly projections with projected_revenue, projected_expenses, projected_profit
- summary: Object with totals (total_projected_revenue, total_projected_expenses, total_projected_profit)
- reasoning: Brief explanation of your projections

Respond ONLY with the JSON object, no other text.
"""

            response = await client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_user_prompt}
                ],
            )

            # Parse JSON from response
            content = response.content[0].text
            result = json.loads(content)
            result["provider"] = "anthropic"
            return result

        except Exception as e:
            logger.error(f"Anthropic API error: {e}, falling back to mock")
            mock = MockLLMProvider()
            result = await mock.generate_scenario(system_prompt, user_prompt, context)
            result["error"] = str(e)
            return result


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get LLM provider.

    Args:
        provider_name: 'openai', 'anthropic', or 'mock'. If None, auto-detects.

    Returns:
        LLM provider instance
    """
    import os

    if provider_name == "mock":
        return MockLLMProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "anthropic":
        return AnthropicProvider()

    # Auto-detect based on available API keys
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicProvider()
    elif os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider()

    # Default to mock
    logger.info("No LLM API keys configured, using mock provider")
    return MockLLMProvider()
