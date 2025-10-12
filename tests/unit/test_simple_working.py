import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ebonhold_chatbot.config import Config
from ebonhold_chatbot.groq_client import GroqClient
from ebonhold_chatbot.knowledge_base import KnowledgeBase


class TestWorkingExamples:
    """
    Working examples that demonstrate the testing approach works.
    These tests show complete mocking of external dependencies using:
    - pytest-mock with mocker.patch
    - parametrized tests with pytest.param and IDs
    - autospec mocking of classes
    """

    def test_config_works(self):
        """Simple config test to verify basic functionality"""
        config = Config(
            discord_token="test_token",
            groq_api_key="test_key"
        )
        assert config.discord_token == "test_token"
        assert config.groq_api_key == "test_key"

    @pytest.mark.parametrize(
        "api_key,model,expected_key,expected_model",
        [
            pytest.param("key1", "model1", "key1", "model1", id="basic_setup"),
            pytest.param("key2", "model2", "key2", "model2", id="different_values"),
        ]
    )
    def test_groq_client_init_parametrized(self, mocker, api_key, model, expected_key, expected_model):
        """Demonstrates parametrized testing with complete mocking"""
        mock_async_groq = mocker.patch("ebonhold_chatbot.groq_client.AsyncGroq")

        client = GroqClient(api_key=api_key, model=model)

        assert client.api_key == expected_key
        assert client.model == expected_model
        mock_async_groq.assert_called_once_with(api_key=api_key)

    async def test_groq_client_generate_response(self, mocker):
        """Demonstrates async testing with complete mocking"""
        mock_async_groq = mocker.patch("ebonhold_chatbot.groq_client.AsyncGroq")
        mock_logger = mocker.patch("ebonhold_chatbot.groq_client.logger")

        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "  Test response from LLM  "
        mock_response.choices = [mock_choice]

        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_groq.return_value = mock_client_instance

        client = GroqClient(api_key="test_key", model="test_model")

        result = await client.generate_response(
            user_query="Test question",
            context="Test context",
            max_tokens=512,
            temperature=0.8
        )

        assert result == "Test response from LLM"
        mock_client_instance.chat.completions.create.assert_called_once()

    def test_knowledge_base_split_text_logic(self):
        """Tests the actual text splitting logic without external dependencies"""
        kb = KnowledgeBase(db_path="test", chunk_size=3, chunk_overlap=1)

        result = kb._split_text("word1 word2 word3 word4 word5")

        # This matches the actual implementation logic
        expected = ["word1 word2 word3", "word3 word4 word5", "word5"]
        assert result == expected

    @pytest.mark.parametrize(
        "text,chunk_size,chunk_overlap,expected_count",
        [
            pytest.param("a b c d e", 2, 0, 3, id="no_overlap"),
            pytest.param("a b c d e", 3, 1, 3, id="with_overlap"),
            pytest.param("single", 10, 2, 1, id="single_word"),
        ]
    )
    def test_knowledge_base_chunking_parametrized(self, text, chunk_size, chunk_overlap, expected_count):
        """Parametrized test of chunking behavior"""
        kb = KnowledgeBase(db_path="test", chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        result = kb._split_text(text)

        assert len(result) == expected_count
        assert all(isinstance(chunk, str) for chunk in result)