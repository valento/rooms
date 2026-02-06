from sentence_transformers import SentenceTransformer
import numpy as np
from config import settings
from .database import execute_query

# Load model once at startup
model = SentenceTransformer(settings.EMBEDDING_MODEL)

def generate_embedding(text: str) -> list:
    """Generate embedding vector for text."""
    embedding = model.encode(text)
    return embedding.tolist()

def semantic_search(query: str, limit: int = 10, threshold: float = 0.5):
    """
    Perform semantic search using pgvector.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        threshold: Minimum similarity threshold (0-1)
    
    Returns:
        List of matching content blocks with similarity scores
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    
    # Convert to pgvector format
    embedding_list = '[' + ','.join(map(str, query_embedding)) + ']'
    
    # Semantic search query using cosine similarity
    sql = """
        SET search_path TO company, public;
        SELECT 
            id,
            block_type,
            title,
            body,
            metadata,
            created_at,
            updated_at,
            1 - (embedding <=> %s::vector) as similarity
        FROM content_blocks
        WHERE embedding IS NOT NULL
            AND 1 - (embedding <=> %s::vector) > %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    
    results = execute_query(
        sql, 
        (embedding_list, embedding_list, threshold, embedding_list, limit)
    )
    
    return results