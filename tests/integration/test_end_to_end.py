import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import asyncio
from pathlib import Path
from ebonhold_chatbot.config import Config
from ebonhold_chatbot.groq_client import GroqClient
from ebonhold_chatbot.knowledge_base import KnowledgeBase
from ebonhold_chatbot.bot import EbonHoldBot


class TestEndToEnd:
    @pytest.fixture
    def temp_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            guide_file = temp_path / "dk_guide.txt"
            guide_file.write_text("""
            Death Knight Guide:

            Death Knights are melee DPS/Tank hybrid class.

            Best DPS rotation:
            1. Apply Plague Strike
            2. Use Death Coil
            3. Cast Death and Decay for AoE

            Talent recommendations:
            - Unholy spec for maximum DPS
            - Blood spec for tanking
            """)

            db_path = temp_path / "test_db"
            db_path.mkdir()

            yield {
                "guide_file": guide_file,
                "db_path": str(db_path),
                "temp_dir": temp_path
            }

    @pytest.fixture
    def integration_config(self, temp_files):
        return Config(
            discord_token="integration_test_token",
            groq_api_key="integration_test_groq_key",
            groq_model="test-model",
            vector_db_path=temp_files["db_path"],
            max_tokens=256,
            temperature=0.3,
            chunk_size=100,
            chunk_overlap=20
        )

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_knowledge_base_full_workflow(self, temp_files):
        kb = KnowledgeBase(
            db_path=temp_files["db_path"],
            chunk_size=50,
            chunk_overlap=10
        )

        with patch("chromadb.PersistentClient") as mock_client_class:
            mock_client = MagicMock()
            mock_collection = MagicMock()

            mock_client_class.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_collection.count.return_value = 0

            await kb.initialize()

            mock_collection.add = MagicMock()
            await kb.load_guide_file(temp_files["guide_file"])

            mock_collection.add.assert_called_once()
            call_args = mock_collection.add.call_args
            assert len(call_args.kwargs["documents"]) > 0
            assert "Death Knight" in " ".join(call_args.kwargs["documents"])

            mock_collection.query.return_value = {
                "documents": [["Death Knights are melee DPS/Tank hybrid class."]],
                "metadatas": [[{"source": str(temp_files["guide_file"])}]]
            }

            result = await kb.search("What are Death Knights?")
            assert "Death Knights are melee DPS/Tank hybrid class." in result

    @pytest.mark.integration
    async def test_groq_client_request_formatting(self):
        with patch("ebonhold_chatbot.groq_client.AsyncGroq") as mock_groq_class:
            mock_groq_instance = AsyncMock()
            mock_groq_class.return_value = mock_groq_instance

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Death Knights excel at melee combat"

            mock_groq_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            client = GroqClient(api_key="test_key", model="test_model")

            result = await client.generate_response(
                user_query="How good are Death Knights?",
                context="Death Knights are powerful warriors",
                max_tokens=512,
                temperature=0.8
            )

            assert result == "Death Knights excel at melee combat"

            call_args = mock_groq_instance.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "test_model"
            assert call_args.kwargs["max_tokens"] == 512
            assert call_args.kwargs["temperature"] == 0.8

            messages = call_args.kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert "Lich King" in messages[0]["content"]
            assert messages[1]["role"] == "user"
            assert "How good are Death Knights?" in messages[1]["content"]
            assert "Death Knights are powerful warriors" in messages[1]["content"]

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_complete_bot_workflow_simulation(
        self,
        integration_config,
        temp_files
    ):
        with patch("ebonhold_chatbot.bot.discord") as mock_discord, \
             patch("ebonhold_chatbot.bot.commands") as mock_commands, \
             patch("chromadb.PersistentClient") as mock_chroma, \
             patch("ebonhold_chatbot.groq_client.AsyncGroq") as mock_groq_class:

            mock_intents = MagicMock()
            mock_discord.Intents.default.return_value = mock_intents
            mock_discord.DMChannel = MagicMock

            mock_chroma_client = MagicMock()
            mock_collection = MagicMock()
            mock_chroma.return_value = mock_chroma_client
            mock_chroma_client.get_or_create_collection.return_value = mock_collection
            mock_collection.count.return_value = 3

            mock_groq_instance = AsyncMock()
            mock_groq_class.return_value = mock_groq_instance

            bot = EbonHoldBot(integration_config)

            await bot.setup_hook()

            await bot.knowledge_base.load_guide_file(temp_files["guide_file"])

            mock_collection.query.return_value = {
                "documents": [["Use Death Coil for single target DPS"]],
                "metadatas": [[{"source": str(temp_files["guide_file"])}]]
            }

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "For optimal DPS, prioritize Death Coil in your rotation."
            mock_groq_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            mock_message = AsyncMock()
            mock_message.content = "What's the best DPS ability?"
            mock_message.author = MagicMock()
            mock_message.channel = MagicMock(spec=mock_discord.DMChannel)
            mock_message.channel.typing.return_value.__aenter__ = AsyncMock()
            mock_message.channel.typing.return_value.__aexit__ = AsyncMock()

            bot.user = MagicMock()
            bot.process_commands = AsyncMock()

            await bot.on_message(mock_message)

            mock_groq_instance.chat.completions.create.assert_called_once()
            mock_message.reply.assert_called_once_with(
                "For optimal DPS, prioritize Death Coil in your rotation."
            )

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "user_queries,expected_knowledge_searches",
        [
            pytest.param(
                ["What is Death Knight?", "How to DPS?", "Best talents?"],
                3,
                id="multiple_questions"
            ),
            pytest.param(
                ["Tell me about tanking", "Gear recommendations"],
                2,
                id="different_topics"
            )
        ]
    )
    async def test_multiple_interactions_workflow(
        self,
        integration_config,
        user_queries,
        expected_knowledge_searches
    ):
        with patch("ebonhold_chatbot.bot.discord") as mock_discord, \
             patch("ebonhold_chatbot.bot.commands") as mock_commands, \
             patch("chromadb.PersistentClient") as mock_chroma, \
             patch("ebonhold_chatbot.groq_client.AsyncGroq") as mock_groq_class:

            mock_intents = MagicMock()
            mock_discord.Intents.default.return_value = mock_intents
            mock_discord.DMChannel = MagicMock

            mock_chroma_client = MagicMock()
            mock_collection = MagicMock()
            mock_chroma.return_value = mock_chroma_client
            mock_chroma_client.get_or_create_collection.return_value = mock_collection
            mock_collection.count.return_value = 5

            mock_collection.query.return_value = {
                "documents": [["Relevant knowledge base content"]],
                "metadatas": [[{"source": "test_guide.txt"}]]
            }

            mock_groq_instance = AsyncMock()
            mock_groq_class.return_value = mock_groq_instance

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Helpful response from LLM"
            mock_groq_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            bot = EbonHoldBot(integration_config)
            bot.user = MagicMock()
            bot.process_commands = AsyncMock()

            await bot.setup_hook()

            for query in user_queries:
                mock_message = AsyncMock()
                mock_message.content = query
                mock_message.author = MagicMock()
                mock_message.channel = MagicMock(spec=mock_discord.DMChannel)
                mock_message.channel.typing.return_value.__aenter__ = AsyncMock()
                mock_message.channel.typing.return_value.__aexit__ = AsyncMock()

                await bot.on_message(mock_message)

                mock_message.reply.assert_called_once_with("Helpful response from LLM")

            assert mock_groq_instance.chat.completions.create.call_count == expected_knowledge_searches

    @pytest.mark.integration
    async def test_configuration_integration_flow(self, temp_files):
        test_env = {
            "DISCORD_TOKEN": "env_discord_token",
            "GROQ_API_KEY": "env_groq_key",
            "GUILD_ID": "123456789"
        }

        with patch.dict("os.environ", test_env, clear=True):
            config = Config.from_env()

            assert config.discord_token == "env_discord_token"
            assert config.groq_api_key == "env_groq_key"
            assert config.guild_id == "123456789"

            with patch("ebonhold_chatbot.bot.discord") as mock_discord, \
                 patch("ebonhold_chatbot.bot.commands") as mock_commands, \
                 patch("chromadb.PersistentClient"), \
                 patch("ebonhold_chatbot.groq_client.AsyncGroq"):

                mock_intents = MagicMock()
                mock_discord.Intents.default.return_value = mock_intents

                bot = EbonHoldBot(config)

                assert bot.config.discord_token == "env_discord_token"
                assert bot.config.groq_api_key == "env_groq_key"
                assert bot.config.guild_id == "123456789"