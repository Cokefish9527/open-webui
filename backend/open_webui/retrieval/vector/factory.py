from open_webui.retrieval.vector.main import VectorDBBase
from open_webui.retrieval.vector.type import VectorType
from open_webui.config import VECTOR_DB, ENABLE_QDRANT_MULTITENANCY_MODE


class Vector:

    @staticmethod
    def get_vector(vector_type: str) -> VectorDBBase:
        """
        get vector db instance by vector type
        """
        if vector_type == VectorType.MILVUS:
            from open_webui.retrieval.vector.dbs.milvus import MilvusClient

            return MilvusClient()
        elif vector_type == VectorType.QDRANT:
            if ENABLE_QDRANT_MULTITENANCY_MODE:
                from open_webui.retrieval.vector.dbs.qdrant_multitenancy import (
                    QdrantClient,
                )

                return QdrantClient()
            else:
                from open_webui.retrieval.vector.dbs.qdrant import QdrantClient

                return QdrantClient()
        elif vector_type == VectorType.PINECONE:
            from open_webui.retrieval.vector.dbs.pinecone import PineconeClient

            return PineconeClient()
        elif vector_type == VectorType.OPENSEARCH:
            from open_webui.retrieval.vector.dbs.opensearch import OpenSearchClient

            return OpenSearchClient()
        elif vector_type == VectorType.PGVECTOR:
            from open_webui.retrieval.vector.dbs.pgvector import PgvectorClient

            return PgvectorClient()
        elif vector_type == VectorType.ELASTICSEARCH:
            from open_webui.retrieval.vector.dbs.elasticsearch import (
                ElasticsearchClient,
            )

            return ElasticsearchClient()
        elif vector_type == VectorType.CHROMA:
            from open_webui.retrieval.vector.dbs.chroma import ChromaClient

            return ChromaClient()
        elif vector_type == "none" or not vector_type:
            # Return a dummy implementation for "none" type
            from open_webui.retrieval.vector.dbs.dummy import DummyClient

            return DummyClient()
        else:
            raise ValueError(f"Unsupported vector type: {vector_type}")


VECTOR_DB_CLIENT = Vector.get_vector(VECTOR_DB)
