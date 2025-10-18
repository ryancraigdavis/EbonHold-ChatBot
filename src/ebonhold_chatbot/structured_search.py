"""
Structured data search for WeakAuras, addons, and other resources.
Uses keyword matching and fuzzy search for better accuracy.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import attrs

logger = logging.getLogger(__name__)


@attrs.define
class WeakAura:
    """Represents a WeakAura entry"""
    name: str
    url: str
    category: str
    specs: List[str]
    keywords: List[str]
    description: str
    priority: str
    boss: Optional[str] = None
    raid: Optional[str] = None


@attrs.define
class StructuredSearch:
    """Handles searching through structured data"""
    data_dir: Path = attrs.field(converter=Path)
    weakauras: List[WeakAura] = attrs.field(factory=list)

    def load_data(self):
        """Load structured data from YAML files"""
        weakauras_file = self.data_dir / "weakauras.yaml"

        if weakauras_file.exists():
            with open(weakauras_file, 'r') as f:
                data = yaml.safe_load(f)

            for wa_data in data.get('weakauras', []):
                wa = WeakAura(
                    name=wa_data['name'],
                    url=wa_data['url'],
                    category=wa_data['category'],
                    specs=wa_data['specs'],
                    keywords=wa_data['keywords'],
                    description=wa_data['description'],
                    priority=wa_data['priority'],
                    boss=wa_data.get('boss'),
                    raid=wa_data.get('raid')
                )
                self.weakauras.append(wa)

            logger.info(f"Loaded {len(self.weakauras)} WeakAuras from structured data")
        else:
            logger.warning(f"WeakAuras file not found: {weakauras_file}")

    def search_weakauras(self, query: str, max_results: int = 5) -> List[WeakAura]:
        """
        Search for WeakAuras using keyword matching.
        Returns ranked results based on relevance.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_results = []

        for wa in self.weakauras:
            score = 0

            # Exact name match (highest score)
            if query_lower in wa.name.lower():
                score += 100

            # Keyword matches
            for keyword in wa.keywords:
                if keyword.lower() in query_lower:
                    score += 50
                # Check for individual word matches
                for word in query_words:
                    if word in keyword.lower():
                        score += 20

            # Description matches
            if any(word in wa.description.lower() for word in query_words):
                score += 10

            # Category matches
            if wa.category.replace('-', ' ') in query_lower:
                score += 30

            # Boss/raid specific matches
            if wa.boss and wa.boss.lower() in query_lower:
                score += 40
            if wa.raid and wa.raid.lower() in query_lower:
                score += 30

            # Priority boost
            if wa.priority == 'essential':
                score += 5

            if score > 0:
                scored_results.append((score, wa))

        # Sort by score (highest first) and return top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [wa for score, wa in scored_results[:max_results]]

    def format_weakaura_results(self, weakauras: List[WeakAura]) -> str:
        """Format WeakAura results for the LLM context"""
        if not weakauras:
            return ""

        formatted = "# Recommended WeakAuras\n\n"

        for wa in weakauras:
            formatted += f"**{wa.name}**\n"
            formatted += f"- URL: {wa.url}\n"
            formatted += f"- Category: {wa.category}\n"
            formatted += f"- Specs: {', '.join(wa.specs)}\n"
            formatted += f"- Description: {wa.description}\n"

            if wa.boss:
                formatted += f"- Boss: {wa.boss}\n"
            if wa.raid:
                formatted += f"- Raid: {wa.raid}\n"

            formatted += f"- Priority: {wa.priority}\n\n"

        return formatted
