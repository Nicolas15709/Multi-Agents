"""
Virtual Agency Memory System - Python Client
Provides unified access to vector store and session store
"""

from .embeddings import EmbeddingProvider, OpenAIEmbeddings, GroqEmbeddings
from .vector_client import VectorClient
from .session_client import SessionClient
from .client import MemoryClient

__all__ = [
    'EmbeddingProvider',
    'OpenAIEmbeddings',
    'GroqEmbeddings',
    'VectorClient',
    'SessionClient',
    'MemoryClient'
]

