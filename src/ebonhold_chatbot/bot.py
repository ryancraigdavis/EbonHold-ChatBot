import asyncio
import logging
import discord
from discord.ext import commands

from .config import Config
from .groq_client import GroqClient
from .knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class EbonHoldBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=None
        )

        self.config = config
        self.groq_client = GroqClient(config.groq_api_key, config.groq_model)
        self.knowledge_base = KnowledgeBase(config.vector_db_path)

    async def setup_hook(self):
        logger.info("Setting up bot...")
        await self.knowledge_base.initialize()
        logger.info("Bot setup complete")

    async def on_ready(self):
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Process commands first
        await self.process_commands(message)

        # If it's a DM or mention, treat as chat
        if isinstance(message.channel, discord.DMChannel) or self.user in message.mentions:
            await self.handle_chat(message)

    async def handle_chat(self, message):
        async with message.channel.typing():
            try:
                # Get relevant context from knowledge base
                context = await self.knowledge_base.search(message.content)

                # Generate response with Groq
                response = await self.groq_client.generate_response(
                    message.content,
                    context,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )

                await message.reply(response)
            except Exception as e:
                logger.error(f"Error handling chat: {e}")
                await message.reply("Sorry, I encountered an error while processing your message.")

async def main():
    logging.basicConfig(level=logging.INFO)

    config = Config.from_env()
    bot = EbonHoldBot(config)

    try:
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())