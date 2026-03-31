"""
MemoryClient - Unified interface for Mission Control Memory
Combines vector store (Supabase) and session store (SQLite)
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from .embeddings import get_embedding_provider, EmbeddingProvider
from .vector_client import VectorClient
from .session_client import SessionClient
from dotenv import load_dotenv

load_dotenv()

class MemoryClient:
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        sqlite_path: Optional[str] = None,
        embedding_provider: Optional[EmbeddingProvider] = None
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector = VectorClient(supabase_url, supabase_key)
        self.session = SessionClient(sqlite_path)

    # ---- Session Operations (async) ----

    async def open_session(self, mission_id: str, agent_id: str) -> str:
        import uuid
        token = f"session:{agent_id}:{int(__import__('time').time())}:{uuid.uuid4().hex[:8]}"
        await self.session.create_session(mission_id, agent_id, token)
        return token

    async def get_session_state(self, session_token: str) -> Dict[str, Any]:
        sess = await self.session.get_session(session_token)
        if not sess:
            raise ValueError(f"Session not found: {session_token}")
        return json.loads(sess['state_json'] or '{}')

    async def update_session(self, session_token: str, new_state: Dict[str, Any], diff_ops: Optional[Dict] = None) -> Dict[str, Any]:
        return await self.session.update_session_state(session_token, new_state, diff_ops)

    async def checkpoint(self, session_token: str, checkpoint_type: str = 'automatic', reason: Optional[str] = None) -> int:
        return await self.session.create_checkpoint(session_token, None, checkpoint_type, reason)

    # ---- Memory Operations (vector store calls are synchronous, run in threadpool) ----

    async def remember(
        self,
        agent_id: str,
        mission_id: str,
        session_id: str,
        content: str,
        memory_type: str = 'observation',
        importance: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        embedding = self.embedding_provider.embed_text(content)
        return await asyncio.to_thread(
            self.vector.insert_agent_memory,
            agent_id=agent_id,
            mission_id=mission_id,
            session_id=session_id,
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )

    async def remember_event(
        self,
        mission_id: str,
        agent_id: str,
        event_type: str,
        description: str,
        payload: Optional[Dict] = None
    ) -> Dict[str, Any]:
        combined = f"{event_type}: {description}\n{json.dumps(payload or {}, sort_keys=True)}"
        embedding = self.embedding_provider.embed_text(combined[:8000])
        return await asyncio.to_thread(
            self.vector.insert_semantic_event,
            mission_id=mission_id,
            agent_id=agent_id,
            event_type=event_type,
            description=description,
            embedding=embedding,
            payload=payload or {}
        )

    async def store_artifact(
        self,
        mission_id: str,
        artifact_type: str,
        title: str,
        content: str,
        created_by: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        combined = f"{title}\n{content}"
        embedding = self.embedding_provider.embed_text(combined[:8000])
        return await asyncio.to_thread(
            self.vector.insert_knowledge_artifact,
            mission_id=mission_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            created_by=created_by
        )

    async def search_memories(
        self,
        query: str,
        agent_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        embedding = self.embedding_provider.embed_text(query)
        return await asyncio.to_thread(
            self.vector.search_agent_memories,
            query_embedding=embedding,
            agent_id=agent_id,
            mission_id=mission_id,
            memory_type=memory_type,
            limit=limit,
            similarity_threshold=threshold
        )

    async def search_artifacts(
        self,
        query: str,
        mission_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        title_contains: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        embedding = self.embedding_provider.embed_text(query)
        return await asyncio.to_thread(
            self.vector.search_knowledge_artifacts,
            query_embedding=embedding,
            mission_id=mission_id,
            artifact_type=artifact_type,
            title_contains=title_contains,
            limit=limit,
            similarity_threshold=threshold
        )
