"""
Provider interface that ClaudeProvider and GeminiProvider both implement.

Modeled on what this app actually calls today (see services/claude_analyzer.py
and services/pricing_researcher.py), not a generic LLM wrapper:
  - analyze_images(): multi-image product analysis -> AnalysisResponse
  - analyze_category_aspects(): refine eBay item specifics for a chosen category
  - research_pricing(): web-grounded competitor pricing -> PricingResponse

Each provider owns its own tool-use/function-calling loop, retry policy, and
JSON-extraction internally. The eBay taxonomy tool *execution* logic
(services/ebay/claude_tools.py's execute_ebay_tool) is pure Python and is
shared by both providers; only the wire-format (tool schema + how tool calls
are surfaced by the model) differs per provider, and lives inside each
provider module.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AIProvider(ABC):
    """A vendor-agnostic entry point for every AI capability this app uses."""

    #: Short identifier written to ProductAnalysis.ai_provider (e.g. "claude", "gemini")
    name: str

    #: Exact model ID written to ProductAnalysis.ai_model (e.g. "claude-sonnet-4-5-20250929")
    model: str

    @abstractmethod
    async def analyze_images(
        self,
        images_data: List[Dict[str, Any]],
        platform: str = "ebay",
        user_context: Optional[str] = None,
        request_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
    ):
        """Analyze one or more product images and return an AnalysisResponse.

        Mirrors ClaudeAnalyzer.analyze_images (services/claude_analyzer.py).
        """
        raise NotImplementedError

    @abstractmethod
    async def analyze_category_aspects(
        self,
        images_data: List[Dict[str, Any]],
        category_id: str,
        category_name: str,
        category_path: str,
        aspects: List[Dict[str, Any]],
        original_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Suggest values for a specific eBay category's item specifics.

        Mirrors ClaudeAnalyzer.analyze_category_aspects.
        """
        raise NotImplementedError

    @abstractmethod
    def research_pricing(
        self,
        product_name: str,
        category: str,
        condition: str,
        platform: str,
    ):
        """Research competitor pricing and return a PricingResponse.

        Mirrors PricingResearcher.research_pricing (services/pricing_researcher.py).
        """
        raise NotImplementedError
