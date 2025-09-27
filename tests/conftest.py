import pytest
import asyncio
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_discord_message():
    """Create a mock Discord message for testing."""
    message = MagicMock()
    message.content = "Test message"
    message.author = MagicMock()
    message.channel = MagicMock()
    message.mentions = []
    message.reply = MagicMock()
    return message


@pytest.fixture
def mock_discord_channel():
    """Create a mock Discord channel for testing."""
    channel = MagicMock()
    channel.typing.return_value.__aenter__ = MagicMock()
    channel.typing.return_value.__aexit__ = MagicMock()
    return channel


@pytest.fixture
def mock_groq_response():
    """Create a mock Groq API response for testing."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = "Mock LLM response"
    response.choices = [choice]
    return response


@pytest.fixture
def mock_chromadb_collection():
    """Create a mock ChromaDB collection for testing."""
    collection = MagicMock()
    collection.count.return_value = 5
    collection.add = MagicMock()
    collection.query.return_value = {
        "documents": [["Mock knowledge base content"]],
        "metadatas": [[{"source": "test_file.txt"}]]
    }
    return collection


@pytest.fixture(autouse=True)
def reset_mocks():
    """Automatically reset all mocks after each test."""
    yield
    # This runs after each test
    # Any cleanup code can go here if needed