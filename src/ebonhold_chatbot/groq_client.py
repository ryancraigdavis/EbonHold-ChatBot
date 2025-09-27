import asyncio
import logging
from groq import AsyncGroq
import attrs

logger = logging.getLogger(__name__)

@attrs.define
class GroqClient:
    api_key: str = attrs.field()
    model: str = attrs.field()
    client: AsyncGroq = attrs.field(init=False)

    def __attrs_post_init__(self):
        self.client = AsyncGroq(api_key=self.api_key)

    async def generate_response(
        self,
        user_query: str,
        context: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(user_query, context)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating Groq response: {e}")
            raise

    def _build_system_prompt(self) -> str:
        return """You are the EbonHold Assistant, a knowledgeable Death Knight expert for World of Warcraft Classic.

You specialize in helping players with:
- Blood Death Knight tanking strategies and rotations
- Frost Death Knight DPS optimization
- Unholy Death Knight gameplay and mechanics
- Death Knight leveling guides and tips
- Gear recommendations and stat priorities
- Talent builds for different content types

Always provide helpful, accurate information based on the context provided. If you don't have specific information about something, say so rather than guessing. Keep responses concise but informative."""

    def _build_user_prompt(self, user_query: str, context: str) -> str:
        if context:
            return f"""Based on the following Death Knight guide information:

{context}

Please answer this question: {user_query}"""
        else:
            return f"Please answer this Death Knight question: {user_query}"