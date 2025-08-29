from typing import Any, Dict, List, Optional

from open_webui.retrieval.vector.main import VectorDBBase, VectorItem, GetResult, SearchResult


class DummyClient(VectorDBBase):
    """
    A dummy vector database client that does nothing.
    This is used when no vector database is configured.
    """

    def has_collection(self, collection_name: str) -> bool:
        return False

    def delete_collection(self, collection_name: str) -> None:
        pass

    def insert(self, collection_name: str, items: List[VectorItem]) -> None:
        pass

    def upsert(self, collection_name: str, items: List[VectorItem]) -> None:
        pass

    def search(
        self, collection_name: str, vectors: List[List[float]], limit: int
    ) -> Optional[SearchResult]:
        return SearchResult(ids=None, documents=None, metadatas=None, distances=None)

    def query(
        self, collection_name: str, filter: Dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        return GetResult(ids=None, documents=None, metadatas=None)

    def get(self, collection_name: str) -> Optional[GetResult]:
        return GetResult(ids=None, documents=None, metadatas=None)

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict] = None,
    ) -> None:
        pass

    def reset(self) -> None:
        pass