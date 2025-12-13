#!/usr/bin/env python3
"""
Build ChromaDB locally from guide files.
Useful for testing and initial setup before syncing to EFS.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ebonhold_chatbot.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def build_chromadb(db_path: str = "./chroma_db"):
    """Build ChromaDB from guide files"""
    logger.info("Building ChromaDB...")

    # Initialize knowledge base
    kb = KnowledgeBase(db_path=db_path)
    await kb.initialize()

    # Clear existing data
    logger.info("Clearing existing collection...")
    await kb.clear_collection()

    # Load guides from data directory
    data_dir = Path(__file__).parent.parent / "src" / "ebonhold_chatbot" / "data"
    logger.info(f"Loading guides from: {data_dir}")
    await kb.load_guides_from_directory(data_dir)

    # Get stats
    stats = await kb.get_stats()
    logger.info(f"✅ ChromaDB built successfully!")
    logger.info(f"   Documents: {stats['document_count']}")
    logger.info(f"   Collection: {stats['collection_name']}")
    logger.info(f"   Path: {stats['db_path']}")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build ChromaDB from guide files")
    parser.add_argument(
        "--db-path",
        default="./chroma_db",
        help="Path to ChromaDB directory (default: ./chroma_db)",
    )

    args = parser.parse_args()

    try:
        stats = asyncio.run(build_chromadb(args.db_path))
        print(f"\n🎉 Success! Created ChromaDB with {stats['document_count']} documents")
        print(f"📁 Location: {args.db_path}")
    except Exception as e:
        logger.error(f"❌ Error building ChromaDB: {e}", exc_info=True)
        sys.exit(1)
