import asyncio
import logging
import os
from pathlib import Path
import aiofiles
import chromadb
from chromadb.config import Settings
import attrs

logger = logging.getLogger(__name__)

@attrs.define
class KnowledgeBase:
    db_path: str = attrs.field()
    collection_name: str = attrs.field(default="dk_guides")
    chunk_size: int = attrs.field(default=1000)
    chunk_overlap: int = attrs.field(default=200)

    client: chromadb.PersistentClient = attrs.field(init=False)
    collection: chromadb.Collection = attrs.field(init=False)

    async def initialize(self):
        await asyncio.get_event_loop().run_in_executor(
            None, self._initialize_sync
        )

    def _initialize_sync(self):
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"ChromaDB initialized with {self.collection.count()} documents")

    async def clear_collection(self):
        """Clear all documents from the collection"""
        await asyncio.get_event_loop().run_in_executor(
            None, self._clear_collection_sync
        )

    def _clear_collection_sync(self):
        """Synchronous method to clear the collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Collection cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    async def load_guides_from_directory(self, guides_dir: str | Path):
        guides_dir = Path(guides_dir)

        if not guides_dir.exists():
            logger.warning(f"Guides directory {guides_dir} does not exist")
            return

        text_files = list(guides_dir.glob("*.txt")) + list(guides_dir.glob("*.md"))

        for file_path in text_files:
            await self.load_guide_file(file_path)

    async def load_guide_file(self, file_path: str | Path):
        file_path = Path(file_path)

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            chunks = self._split_text(content)

            documents = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                doc_id = f"{file_path.stem}_{i}"
                documents.append(chunk)
                metadatas.append({
                    "source": str(file_path),
                    "chunk_index": i,
                    "filename": file_path.name
                })
                ids.append(doc_id)

            # Run the blocking operation in executor
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            )

            logger.info(f"Loaded {len(chunks)} chunks from {file_path.name}")

        except Exception as e:
            logger.error(f"Error loading guide file {file_path}: {e}")

    async def search(self, query: str, n_results: int = 5) -> str:
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
            )

            if not results['documents'] or not results['documents'][0]:
                return ""

            # Combine the most relevant chunks
            context_chunks = results['documents'][0]
            return "\n\n".join(context_chunks)

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return ""

    def _split_text(self, text: str) -> list[str]:
        words = text.split()
        chunks = []

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = " ".join(chunk_words)
            chunks.append(chunk)

        return chunks

    async def get_stats(self) -> dict:
        count = await asyncio.get_event_loop().run_in_executor(
            None, self.collection.count
        )

        return {
            "document_count": count,
            "collection_name": self.collection_name,
            "db_path": self.db_path
        }