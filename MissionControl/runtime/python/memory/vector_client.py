"""
Vector Store client - Supabase pgvector operations
"""

import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from postgrest import APIResponse

class VectorClient:
    def __init__(self, url: str = None, key: str = None):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        self.client: Client = create_client(self.url, self.key)

    async def insert_agent_memory(self, **params) -> Dict[str, Any]:
        response = self.client.table('agent_memories').insert(params).execute()
        if response.error:
            raise Exception(f"Insert failed: {response.error}")
        return response.data[0]

    async def insert_semantic_event(self, **params) -> Dict[str, Any]:
        response = self.client.table('semantic_events').insert(params).execute()
        if response.error:
            raise Exception(f"Insert failed: {response.error}")
        return response.data[0]

    async def insert_knowledge_artifact(self, **params) -> Dict[str, Any]:
        response = self.client.table('knowledge_artifacts').insert(params).execute()
        if response.error:
            raise Exception(f"Insert failed: {response.error}")
        return response.data[0]

    async def search_agent_memories(
        self,
        query_embedding: List[float],
        agent_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        # NOTE: Supabase JS client uses RPC or raw SQL for similarity search
        # We'll use a stored procedure or raw query
        # For simplicity, use RPC function defined in Supabase
        params = {
            'query_embedding': query_embedding,
            'limit': limit,
            'similarity_threshold': similarity_threshold
        }
        if agent_id:
            params['agent_id'] = agent_id
        if mission_id:
            params['mission_id'] = mission_id
        if memory_type:
            params['memory_type'] = memory_type

        response = self.client.rpc('search_agent_memories', params).execute()
        if response.error:
            raise Exception(f"Search failed: {response.error}")
        return response.data

    async def get_recent_memories(self, agent_id: str, limit: int = 50, mission_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.client.table('agent_memories').select('*').eq('agent_id', agent_id).order('created_at', desc=True).limit(limit)
        if mission_id:
            query = query.eq('mission_id', mission_id)
        response = query.execute()
        if response.error:
            raise Exception(f"Fetch failed: {response.error}")
        return response.data

    async def cleanup_old_records(self, table: str, older_than_days: int) -> int:
        # This would require a stored procedure or raw SQL with proper permissions
        raise NotImplementedError("Use the cleanup job from Node side or create a Supabase Edge Function")
