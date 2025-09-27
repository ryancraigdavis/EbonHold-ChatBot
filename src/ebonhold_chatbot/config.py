import os
import attrs

@attrs.define
class Config:
    discord_token: str = attrs.field()
    groq_api_key: str = attrs.field()
    guild_id: str | None = attrs.field(default=None)

    # Groq settings
    groq_model: str = attrs.field(default="llama-3.1-8b-instant")
    max_tokens: int = attrs.field(default=1024)
    temperature: float = attrs.field(default=0.7)

    # Bot settings
    command_prefix: str = attrs.field(default="!")
    bot_name: str = attrs.field(default="EbonHold Assistant")

    # Vector DB settings
    vector_db_path: str = attrs.field(default="./chroma_db")
    chunk_size: int = attrs.field(default=1000)
    chunk_overlap: int = attrs.field(default=200)

    @classmethod
    def from_env(cls) -> "Config":
        discord_token = os.getenv("DISCORD_TOKEN")
        groq_api_key = os.getenv("GROQ_API_KEY")

        if not discord_token:
            raise ValueError("DISCORD_TOKEN environment variable is required")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

        return cls(
            discord_token=discord_token,
            groq_api_key=groq_api_key,
            guild_id=os.getenv("GUILD_ID")
        )