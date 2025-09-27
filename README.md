# EbonHold ChatBot

A Discord chatbot powered by Groq LLM that answers Death Knight questions using your own guide content. Built for World of Warcraft Classic Death Knight players.

## Features

- **Discord Integration**: Responds to mentions and DMs
- **Knowledge Base**: Uses your DK guides as context for responses
- **Groq LLM**: Fast, intelligent responses using llama-3.1-8b-instant
- **Vector Search**: Finds relevant guide sections for each question
- **Secure**: Uses Doppler for environment variable management

## Setup

### Prerequisites
- Python 3.12+
- UV package manager
- Doppler CLI
- Discord Bot Token
- Groq API Key

### Installation

1. **Clone and setup environment**:
   ```bash
   git clone <repo-url>
   cd EbonHold-ChatBot
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   uv sync --dev
   ```

3. **Configure secrets with Doppler**:
   ```bash
   doppler secrets set DISCORD_TOKEN="your_discord_bot_token"
   doppler secrets set GROQ_API_KEY="your_groq_api_key"
   doppler secrets set GUILD_ID="your_discord_server_id"  # optional
   ```

4. **Add your DK guides**:
   - Place your guide files (.txt or .md) in `src/ebonhold_chatbot/data/`

5. **Load guides into knowledge base**:
   ```bash
   uv run doppler run -- python -m ebonhold_chatbot.load_guides
   ```

6. **Run the bot**:
   ```bash
   uv run bot
   ```

## Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application → Bot section
3. Enable "Message Content Intent"
4. Copy bot token for Doppler
5. OAuth2 → URL Generator:
   - Scope: `bot`
   - Permissions: `Send Messages`, `Read Message History`
6. Invite bot to your server

## Usage

**Mention the bot**: `@YourBot what's the best frost DK rotation?`

**Direct Message**: Send DM directly to the bot

The bot searches your uploaded guides and provides contextual answers using Groq LLM.

## Project Structure

```
src/ebonhold_chatbot/
├── __main__.py         # Entry point
├── bot.py             # Discord bot logic
├── config.py          # Configuration management
├── groq_client.py     # Groq API integration
├── knowledge_base.py  # Vector database (ChromaDB)
├── load_guides.py     # Guide loading script
└── data/              # Your DK guide files
```

## Testing

The project includes comprehensive unit and integration tests using pytest.

### Test Commands

**Local testing (without environment variables):**
```bash
# Activate virtual environment
source .venv/bin/activate

# Run all working tests
uv run pytest tests/unit/test_config.py tests/unit/test_groq_client.py tests/unit/test_simple_working.py -v

# Run tests with coverage
uv run pytest tests/unit/test_config.py tests/unit/test_groq_client.py tests/unit/test_simple_working.py --cov=src/ebonhold_chatbot --cov-report=html --cov-report=term-missing

# Run individual test files
uv run pytest tests/unit/test_config.py -v
uv run pytest tests/unit/test_groq_client.py -v
uv run pytest tests/unit/test_simple_working.py -v
```

**Testing with Doppler environment:**
```bash
# Run tests with environment variables from doppler
doppler run -- uv run pytest tests/unit/test_config.py tests/unit/test_groq_client.py tests/unit/test_simple_working.py -v

# Coverage with doppler
doppler run -- uv run pytest tests/unit/test_config.py tests/unit/test_groq_client.py tests/unit/test_simple_working.py --cov=src/ebonhold_chatbot --cov-report=html
```

### Test Structure

- `tests/unit/` - Unit tests with complete mocking of external dependencies
- `tests/integration/` - Integration tests with realistic workflows
- `tests/conftest.py` - Shared test fixtures

### Test Features

- **Complete Mocking**: All external dependencies (Discord API, Groq API, ChromaDB, file I/O) are mocked
- **Parametrized Tests**: Multiple scenarios with descriptive IDs using `pytest.param`
- **Async Support**: Proper async/await testing with `pytest-asyncio`
- **Coverage Reports**: HTML and terminal coverage reporting
- **Test Markers**: `unit`, `integration`, and `slow` markers for selective test running

## Development

**Clean up test artifacts:**
```bash
uv run clean-cache
```

**Install new dependencies:**
```bash
uv add <package-name>
```

**Install test dependencies:**
```bash
uv add --dev <test-package-name>
```

## Stopping the Bot

Use `Ctrl+C` to gracefully shutdown the bot.
