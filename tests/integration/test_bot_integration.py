import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import tempfile
import os
from pathlib import Path
from ebonhold_chatbot.bot import EbonHoldBot, main
from ebonhold_chatbot.config import Config


class TestBotIntegration:
    @pytest.fixture
    def temp_db_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_config(self, temp_db_path):
        return Config(
            discord_token="test_discord_token",
            groq_api_key="test_groq_key",
            groq_model="test_model",
            vector_db_path=temp_db_path,
            max_tokens=512,
            temperature=0.5
        )

    @pytest.fixture
    def mock_discord_components(self, mocker):
        mock_discord = mocker.patch("ebonhold_chatbot.bot.discord")
        mock_commands = mocker.patch("ebonhold_chatbot.bot.commands")

        mock_intents = MagicMock()
        mock_discord.Intents.default.return_value = mock_intents
        mock_discord.DMChannel = MagicMock

        return {
            "discord": mock_discord,
            "commands": mock_commands,
            "intents": mock_intents
        }

    @pytest.fixture
    def mock_external_services(self, mocker):
        mock_groq = mocker.patch("ebonhold_chatbot.bot.GroqClient")
        mock_kb = mocker.patch("ebonhold_chatbot.bot.KnowledgeBase")

        mock_groq_instance = AsyncMock()
        mock_groq_instance.generate_response = AsyncMock(return_value="Mocked LLM response")
        mock_groq.return_value = mock_groq_instance

        mock_kb_instance = AsyncMock()
        mock_kb_instance.initialize = AsyncMock()
        mock_kb_instance.search = AsyncMock(return_value="Mocked knowledge context")
        mock_kb.return_value = mock_kb_instance

        return {
            "groq_class": mock_groq,
            "groq_instance": mock_groq_instance,
            "kb_class": mock_kb,
            "kb_instance": mock_kb_instance
        }

    @pytest.mark.integration
    async def test_bot_initialization_flow(
        self,
        mock_config,
        mock_discord_components,
        mock_external_services
    ):
        bot = EbonHoldBot(mock_config)

        assert bot.config == mock_config
        assert bot.groq_client == mock_external_services["groq_instance"]
        assert bot.knowledge_base == mock_external_services["kb_instance"]

        mock_external_services["groq_class"].assert_called_once_with(
            mock_config.groq_api_key,
            mock_config.groq_model
        )
        mock_external_services["kb_class"].assert_called_once_with(
            mock_config.vector_db_path
        )

    @pytest.mark.integration
    async def test_setup_hook_integration(
        self,
        mock_config,
        mock_discord_components,
        mock_external_services,
        mocker
    ):
        mock_logger = mocker.patch("ebonhold_chatbot.bot.logger")
        bot = EbonHoldBot(mock_config)

        await bot.setup_hook()

        mock_external_services["kb_instance"].initialize.assert_called_once()
        assert mock_logger.info.call_count == 2

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "message_scenario,expected_behavior",
        [
            pytest.param(
                {
                    "content": "How do I play Death Knight?",
                    "is_dm": True,
                    "mentions_bot": False,
                    "is_bot_author": False
                },
                {
                    "should_search_kb": True,
                    "should_generate_response": True,
                    "should_reply": True
                },
                id="dm_message_workflow"
            ),
            pytest.param(
                {
                    "content": "@bot What's the best talent build?",
                    "is_dm": False,
                    "mentions_bot": True,
                    "is_bot_author": False
                },
                {
                    "should_search_kb": True,
                    "should_generate_response": True,
                    "should_reply": True
                },
                id="mention_message_workflow"
            ),
            pytest.param(
                {
                    "content": "Random guild chat message",
                    "is_dm": False,
                    "mentions_bot": False,
                    "is_bot_author": False
                },
                {
                    "should_search_kb": False,
                    "should_generate_response": False,
                    "should_reply": False
                },
                id="ignored_guild_message"
            ),
            pytest.param(
                {
                    "content": "Bot's own message",
                    "is_dm": True,
                    "mentions_bot": False,
                    "is_bot_author": True
                },
                {
                    "should_search_kb": False,
                    "should_generate_response": False,
                    "should_reply": False
                },
                id="bot_own_message_ignored"
            )
        ]
    )
    async def test_message_processing_workflow(
        self,
        mock_config,
        mock_discord_components,
        mock_external_services,
        message_scenario,
        expected_behavior
    ):
        bot = EbonHoldBot(mock_config)
        bot.process_commands = AsyncMock()

        mock_message = AsyncMock()
        mock_message.content = message_scenario["content"]
        mock_message.reply = AsyncMock()

        bot.user = MagicMock()
        if message_scenario["is_bot_author"]:
            mock_message.author = bot.user
        else:
            mock_message.author = MagicMock()

        if message_scenario["is_dm"]:
            mock_message.channel = MagicMock(spec=mock_discord_components["discord"].DMChannel)
        else:
            mock_message.channel = MagicMock()

        if message_scenario["mentions_bot"]:
            mock_message.mentions = [bot.user]
        else:
            mock_message.mentions = []

        mock_message.channel.typing.return_value.__aenter__ = AsyncMock()
        mock_message.channel.typing.return_value.__aexit__ = AsyncMock()

        await bot.on_message(mock_message)

        if expected_behavior["should_search_kb"]:
            mock_external_services["kb_instance"].search.assert_called_once_with(
                message_scenario["content"]
            )
        else:
            mock_external_services["kb_instance"].search.assert_not_called()

        if expected_behavior["should_generate_response"]:
            mock_external_services["groq_instance"].generate_response.assert_called_once()
        else:
            mock_external_services["groq_instance"].generate_response.assert_not_called()

        if expected_behavior["should_reply"]:
            mock_message.reply.assert_called_once()
        else:
            mock_message.reply.assert_not_called()

    @pytest.mark.integration
    async def test_full_chat_response_pipeline(
        self,
        mock_config,
        mock_discord_components,
        mock_external_services
    ):
        bot = EbonHoldBot(mock_config)
        bot.process_commands = AsyncMock()

        mock_message = AsyncMock()
        mock_message.content = "What's the best DPS rotation?"
        mock_message.author = MagicMock()
        mock_message.channel = MagicMock(spec=mock_discord_components["discord"].DMChannel)
        mock_message.channel.typing.return_value.__aenter__ = AsyncMock()
        mock_message.channel.typing.return_value.__aexit__ = AsyncMock()
        mock_message.reply = AsyncMock()

        bot.user = MagicMock()

        mock_external_services["kb_instance"].search.return_value = "Knowledge base context about DPS"
        mock_external_services["groq_instance"].generate_response.return_value = "Use Death Coil and Plague Strike"

        await bot.on_message(mock_message)

        mock_external_services["kb_instance"].search.assert_called_once_with(
            "What's the best DPS rotation?"
        )

        mock_external_services["groq_instance"].generate_response.assert_called_once_with(
            "What's the best DPS rotation?",
            "Knowledge base context about DPS",
            max_tokens=mock_config.max_tokens,
            temperature=mock_config.temperature
        )

        mock_message.reply.assert_called_once_with("Use Death Coil and Plague Strike")

    @pytest.mark.integration
    async def test_error_handling_integration(
        self,
        mock_config,
        mock_discord_components,
        mock_external_services,
        mocker
    ):
        mock_logger = mocker.patch("ebonhold_chatbot.bot.logger")
        bot = EbonHoldBot(mock_config)
        bot.process_commands = AsyncMock()

        mock_message = AsyncMock()
        mock_message.content = "Test message"
        mock_message.author = MagicMock()
        mock_message.channel = MagicMock(spec=mock_discord_components["discord"].DMChannel)
        mock_message.channel.typing.return_value.__aenter__ = AsyncMock()
        mock_message.channel.typing.return_value.__aexit__ = AsyncMock()
        mock_message.reply = AsyncMock()

        bot.user = MagicMock()

        mock_external_services["kb_instance"].search.side_effect = Exception("Knowledge base error")

        await bot.on_message(mock_message)

        mock_logger.error.assert_called_once()
        mock_message.reply.assert_called_once_with(
            "Sorry, I encountered an error while processing your message."
        )

    @pytest.mark.integration
    async def test_main_function_integration(self, mocker):
        mock_logging = mocker.patch("ebonhold_chatbot.bot.logging")
        mock_config_class = mocker.patch("ebonhold_chatbot.bot.Config")
        mock_bot_class = mocker.patch("ebonhold_chatbot.bot.EbonHoldBot")

        mock_config = MagicMock()
        mock_config.discord_token = "test_token"
        mock_config_class.from_env.return_value = mock_config

        mock_bot = AsyncMock()
        mock_bot.start = AsyncMock()
        mock_bot.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        await main()

        mock_logging.basicConfig.assert_called_once_with(level=mock_logging.INFO)
        mock_config_class.from_env.assert_called_once()
        mock_bot_class.assert_called_once_with(mock_config)
        mock_bot.start.assert_called_once_with("test_token")

    @pytest.mark.integration
    async def test_main_function_keyboard_interrupt(self, mocker):
        mock_logging = mocker.patch("ebonhold_chatbot.bot.logging")
        mock_logger = mocker.patch("ebonhold_chatbot.bot.logger")
        mock_config_class = mocker.patch("ebonhold_chatbot.bot.Config")
        mock_bot_class = mocker.patch("ebonhold_chatbot.bot.EbonHoldBot")

        mock_config = MagicMock()
        mock_config.discord_token = "test_token"
        mock_config_class.from_env.return_value = mock_config

        mock_bot = AsyncMock()
        mock_bot.start = AsyncMock(side_effect=KeyboardInterrupt())
        mock_bot.close = AsyncMock()
        mock_bot_class.return_value = mock_bot

        await main()

        mock_bot.start.assert_called_once_with("test_token")
        mock_logger.info.assert_called_with("Shutting down bot...")
        mock_bot.close.assert_called_once()