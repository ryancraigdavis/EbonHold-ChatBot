import pytest
from unittest.mock import patch
from ebonhold_chatbot.config import Config


class TestConfig:
    @pytest.fixture
    def mock_config(self, mocker):
        return mocker.create_autospec(Config, spec_set=True)

    @pytest.mark.parametrize(
        "env_vars,expected_result",
        [
            pytest.param(
                {
                    "DISCORD_TOKEN": "test_discord_token",
                    "GROQ_API_KEY": "test_groq_key",
                    "GUILD_ID": "123456789"
                },
                {
                    "discord_token": "test_discord_token",
                    "groq_api_key": "test_groq_key",
                    "guild_id": "123456789"
                },
                id="all_env_vars_set"
            ),
            pytest.param(
                {
                    "DISCORD_TOKEN": "test_discord_token",
                    "GROQ_API_KEY": "test_groq_key"
                },
                {
                    "discord_token": "test_discord_token",
                    "groq_api_key": "test_groq_key",
                    "guild_id": None
                },
                id="optional_guild_id_not_set"
            )
        ]
    )
    def test_from_env_success(self, mocker, env_vars, expected_result):
        with patch.dict("os.environ", env_vars, clear=True):
            config = Config.from_env()

            assert config.discord_token == expected_result["discord_token"]
            assert config.groq_api_key == expected_result["groq_api_key"]
            assert config.guild_id == expected_result["guild_id"]

    @pytest.mark.parametrize(
        "env_vars,expected_error",
        [
            pytest.param(
                {"GROQ_API_KEY": "test_groq_key"},
                "DISCORD_TOKEN environment variable is required",
                id="missing_discord_token"
            ),
            pytest.param(
                {"DISCORD_TOKEN": "test_discord_token"},
                "GROQ_API_KEY environment variable is required",
                id="missing_groq_api_key"
            ),
            pytest.param(
                {},
                "DISCORD_TOKEN environment variable is required",
                id="missing_both_tokens"
            )
        ]
    )
    def test_from_env_missing_required_vars(self, env_vars, expected_error):
        with patch.dict("os.environ", env_vars, clear=True):
            with pytest.raises(ValueError, match=expected_error):
                Config.from_env()

    def test_config_defaults(self):
        config = Config(
            discord_token="test_token",
            groq_api_key="test_key"
        )

        assert config.groq_model == "llama-3.1-8b-instant"
        assert config.max_tokens == 1024
        assert config.temperature == 0.7
        assert config.command_prefix == "!"
        assert config.bot_name == "EbonHold Assistant"
        assert config.vector_db_path == "./chroma_db"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200

    def test_config_custom_values(self):
        config = Config(
            discord_token="test_token",
            groq_api_key="test_key",
            groq_model="custom-model",
            max_tokens=2048,
            temperature=0.5,
            command_prefix="?",
            bot_name="Custom Bot",
            vector_db_path="/custom/path",
            chunk_size=500,
            chunk_overlap=100
        )

        assert config.groq_model == "custom-model"
        assert config.max_tokens == 2048
        assert config.temperature == 0.5
        assert config.command_prefix == "?"
        assert config.bot_name == "Custom Bot"
        assert config.vector_db_path == "/custom/path"
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100