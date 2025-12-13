"""
AWS Lambda handler for Discord Interactions API.
Handles slash commands with ChromaDB on EFS.
"""

import json
import logging
import os
import asyncio
from pathlib import Path
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# Import from the main package
import sys
sys.path.insert(0, '/opt/python')  # Lambda layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ebonhold_chatbot.config import Config
from ebonhold_chatbot.groq_client import GroqClient
from ebonhold_chatbot.knowledge_base import KnowledgeBase
from ebonhold_chatbot.structured_search import StructuredSearch

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global variables for warm starts (reused across invocations)
knowledge_base = None
groq_client = None
structured_search = None
config = None


def verify_discord_signature(event):
    """Verify the request came from Discord"""
    public_key = os.getenv('DISCORD_PUBLIC_KEY')
    verify_key = VerifyKey(bytes.fromhex(public_key))

    signature = event['headers'].get('x-signature-ed25519')
    timestamp = event['headers'].get('x-signature-timestamp')
    body = event['body']

    try:
        verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
        return True
    except BadSignatureError:
        return False


async def initialize_services():
    """Initialize services on cold start (cached for warm starts)"""
    global knowledge_base, groq_client, structured_search, config

    if knowledge_base is not None:
        logger.info("Warm start - reusing existing services")
        return

    logger.info("Cold start - initializing services")

    # Load config
    config = Config.from_env()

    # Initialize Groq client
    groq_client = GroqClient(config.groq_api_key, config.groq_model)

    # Initialize knowledge base pointing to EFS mount
    # EFS will be mounted at /mnt/efs
    efs_path = os.getenv('EFS_MOUNT_PATH', '/mnt/efs/chroma_db')
    knowledge_base = KnowledgeBase(db_path=efs_path)
    await knowledge_base.initialize()

    # Initialize structured search - data will be bundled in Lambda package
    data_dir = Path(__file__).parent.parent / "src" / "ebonhold_chatbot" / "data"
    structured_search = StructuredSearch(data_dir=data_dir)
    structured_search.load_data()

    stats = await knowledge_base.get_stats()
    logger.info(f"Services initialized. KB stats: {stats}")


async def handle_slash_command(interaction_data):
    """Handle /lich slash command"""
    # Extract the user's question
    options = interaction_data.get('data', {}).get('options', [])
    if not options:
        return {
            "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "content": "Please provide a question! Usage: `/lich <your question>`"
            }
        }

    query = options[0].get('value', '')

    if not query:
        return {
            "type": 4,
            "data": {
                "content": "Please provide a question!"
            }
        }

    logger.info(f"Processing query: {query}")

    try:
        # Hybrid search: structured data + vector search
        context_parts = []

        # 1. Search structured WeakAura data
        weakauras = structured_search.search_weakauras(query)
        if weakauras:
            wa_context = structured_search.format_weakaura_results(weakauras)
            context_parts.append(wa_context)
            logger.info(f"Found {len(weakauras)} WeakAuras from structured search")

        # 2. Get relevant context from vector knowledge base
        vector_context = await knowledge_base.search(query, n_results=5)
        if vector_context:
            context_parts.append("# Additional Information\n\n" + vector_context)

        # Combine contexts
        context = "\n\n".join(context_parts) if context_parts else ""

        # Generate response with Groq
        response = await groq_client.generate_response(
            query,
            context,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        # Discord has a 2000 character limit for messages
        if len(response) > 2000:
            response = response[:1997] + "..."

        return {
            "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "content": response
            }
        }

    except Exception as e:
        logger.error(f"Error processing command: {e}", exc_info=True)
        return {
            "type": 4,
            "data": {
                "content": "Sorry, I encountered an error while processing your question. Please try again."
            }
        }


def lambda_handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Received event: {json.dumps(event)}")

    # Verify Discord signature
    if not verify_discord_signature(event):
        logger.warning("Invalid signature")
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Invalid signature'})
        }

    # Parse the interaction
    interaction = json.loads(event['body'])
    interaction_type = interaction.get('type')

    # Type 1: PING (Discord verification)
    if interaction_type == 1:
        logger.info("Responding to Discord PING")
        return {
            'statusCode': 200,
            'body': json.dumps({'type': 1})
        }

    # Type 2: APPLICATION_COMMAND (slash command)
    if interaction_type == 2:
        # Initialize services if needed
        loop = asyncio.get_event_loop()
        loop.run_until_complete(initialize_services())

        # Handle the command
        response = loop.run_until_complete(handle_slash_command(interaction))

        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }

    # Unknown interaction type
    logger.warning(f"Unknown interaction type: {interaction_type}")
    return {
        'statusCode': 400,
        'body': json.dumps({'error': 'Unknown interaction type'})
    }
