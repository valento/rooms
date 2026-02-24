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

def semantic_search(query: str, user_id: int = None, limit: int = 10, threshold: float = 0.5):
    """
    Perform semantic search using pgvector.
    
    Args:
        query: Search query text
        user_id: Optional logged-in user for personalization
        limit: Maximum number of results
        threshold: Minimum similarity threshold (0-1)
    
    Returns:
        List of matching content blocks with similarity scores
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    
    # Convert to pgvector format
    embedding_list = '[' + ','.join(map(str, query_embedding)) + ']'
    
    sql = """
        
        SET search_path TO company, public;
        SELECT 
            cb.id,
            cb.title,
            cb.body,
            cb.deck,
            cb.slug,
            cb.metadata,
            cb.author_id,
            cb.view_count,
            cb.social_score,
            cb.priority,
            cb.created_at,
            cb.updated_at,
            1 - (cb.embedding <=> %s::vector) AS semantic_similarity,
            CASE WHEN uf.id IS NOT NULL THEN 1 ELSE 0 END AS is_followed_author,
            (
                (1 - (cb.embedding <=> %s::vector)) * 10 +
                COALESCE(cb.social_score, 0) * 0.1 +
                COALESCE(cb.priority, 0) * 0.5 +
                CASE WHEN uf.id IS NOT NULL THEN 5 ELSE 0 END
            ) AS final_score
        FROM content_blocks cb
        LEFT JOIN user_follows uf 
            ON cb.author_id = uf.following_id 
            AND uf.follower_id = %s
        WHERE cb.embedding IS NOT NULL
            AND 1 - (cb.embedding <=> %s::vector) > %s
        ORDER BY final_score DESC
        LIMIT %s
    """
    # SET search_path TO company, public;
    #     SELECT 
    #         id,
    #         title,
    #         body,
    #         metadata,
    #         created_at,
    #         updated_at,
    #         1 - (embedding <=> %s::vector) as semantic_similarity,
    #         COALESCE((metadata->>'priority')::int, 5) as priority,
    #         (1 - (embedding <=> %s::vector)) * 0.7 + 
    #         (COALESCE((metadata->>'priority')::int, 5) / 10.0) * 0.3 as final_score
    #     FROM content_blocks
    #     WHERE embedding IS NOT NULL
    #         AND 1 - (embedding <=> %s::vector) > %s
    #     ORDER BY final_score DESC
    #     LIMIT %s

    results = execute_query(
        sql, 
        # (embedding_list, embedding_list, embedding_list, threshold, limit)
        (embedding_list, embedding_list, user_id, embedding_list, threshold, limit)
    )


    # Semantic search query using cosine similarity
    # sql = """
    #     SET search_path TO company, public;
    #     SELECT 
    #         id,
    #         title,
    #         body,
    #         metadata,
    #         created_at,
    #         updated_at,
    #         1 - (embedding <=> %s::vector) as similarity
    #     FROM content_blocks
    #     WHERE embedding IS NOT NULL
    #         AND 1 - (embedding <=> %s::vector) > %s
    #     ORDER BY embedding <=> %s::vector
    #     LIMIT %s
    # """
    
    # results = execute_query(
    #     sql, 
    #     (embedding_list, embedding_list, threshold, embedding_list, limit)
    # )
    
    return results