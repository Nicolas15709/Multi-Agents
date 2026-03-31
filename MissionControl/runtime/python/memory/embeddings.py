"""
Embeddings provider for Python agents
Supports OpenAI and Groq
"""

import os
from abc import ABC, abstractmethod
from typing import List
import numpy as np
from openai import OpenAI, AsyncOpenAI
from groq import Groq, AsyncGroq
import hashlib

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

class OpenAIEmbeddings(EmbeddingProvider):
    def __init__(self, api_key: str = None, model: str = "text-embedding-ada-002"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self._cache = {}

    def _cache_key(self, text: str):
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"{self.model}:{h}"

    def embed_text(self, text: str) -> List[float]:
        text = text[:8000]  # limit
        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = self.client.embeddings.create(input=text, model=self.model)
        embedding = response.data[0].embedding
        self._cache[cache_key] = embedding
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            results.append(self.embed_text(text))
        return results

class GroqEmbeddings(EmbeddingProvider):
    def __init__(self, api_key: str = None, model: str = "text-embedding-ada-002"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")
        self.model = model
        self.client = Groq(api_key=self.api_key)
        self._cache = {}

    def _cache_key(self, text: str):
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"{self.model}:{h}"

    def embed_text(self, text: str) -> List[float]:
        text = text[:8000]
        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = self.client.embeddings.create(input=text, model=self.model)
        embedding = response.data[0].embedding
        self._cache[cache_key] = embedding
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            results.append(self.embed_text(text))
        return results

def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    if provider == "openai":
        return OpenAIEmbeddings()
    elif provider == "groq":
        return GroqEmbeddings()
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
