import pytest
from unittest.mock import AsyncMock, MagicMock
from ebonhold_chatbot.groq_client import GroqClient


class TestGroqClient:
    @pytest.fixture
    def mock_async_groq(self, mocker):
        return mocker.patch("ebonhold_chatbot.groq_client.AsyncGroq")

    def test_init(self, mock_async_groq):
        client = GroqClient(api_key="test_key", model="test_model")

        assert client.api_key == "test_key"
        assert client.model == "test_model"
        mock_async_groq.assert_called_once_with(api_key="test_key")

    @pytest.mark.parametrize(
        "user_query,context,max_tokens,temperature,expected_response",
        [
            pytest.param(
                "What is Death Knight?",
                "Death Knights are undead warriors",
                1024,
                0.7,
                "Death Knights are powerful undead warriors in World of Warcraft.",
                id="with_context"
            ),
            pytest.param(
                "How to level?",
                "",
                512,
                0.5,
                "Start by doing quests in the starting zone.",
                id="without_context"
            ),
            pytest.param(
                "Best talent build?",
                "Unholy is the best DPS spec",
                2048,
                0.9,
                "For DPS, go with Unholy spec for maximum damage output.",
                id="custom_parameters"
            )
        ]
    )
    async def test_generate_response_success(
        self,
        mock_async_groq,
        user_query,
        context,
        max_tokens,
        temperature,
        expected_response
    ):
        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = f"  {expected_response}  "
        mock_response.choices = [mock_choice]

        # Setup mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_async_groq.return_value = mock_client_instance

        client = GroqClient(api_key="test_api_key", model="test_model")

        result = await client.generate_response(
            user_query=user_query,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature
        )

        assert result == expected_response

        # Verify the API call
        mock_client_instance.chat.completions.create.assert_called_once()
        call_args = mock_client_instance.chat.completions.create.call_args

        assert call_args.kwargs["model"] == "test_model"
        assert call_args.kwargs["max_tokens"] == max_tokens
        assert call_args.kwargs["temperature"] == temperature
        assert len(call_args.kwargs["messages"]) == 2
        assert call_args.kwargs["messages"][0]["role"] == "system"
        assert call_args.kwargs["messages"][1]["role"] == "user"

    def test_build_system_prompt(self, mock_async_groq):
        client = GroqClient(api_key="test_api_key", model="test_model")
        system_prompt = client._build_system_prompt()

        assert "Lich King" in system_prompt
        assert "Death Knight" in system_prompt
        assert "Unholy" in system_prompt
        assert "World of Warcraft Classic" in system_prompt