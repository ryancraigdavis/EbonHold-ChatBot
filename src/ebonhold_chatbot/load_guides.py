import asyncio
import logging
from pathlib import Path

from .config import Config
from .knowledge_base import KnowledgeBase

async def load_all_guides():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    config = Config.from_env()
    kb = KnowledgeBase(config.vector_db_path)

    await kb.initialize()

    # Clear existing collection to avoid stale data
    logger.info("Clearing existing knowledge base...")
    await kb.clear_collection()

    # Load guides from the data directory
    data_dir = Path(__file__).parent / "data"
    await kb.load_guides_from_directory(data_dir)

    stats = await kb.get_stats()
    logger.info(f"Loading complete! Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(load_all_guides())