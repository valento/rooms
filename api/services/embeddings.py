from sentence_transformers import SentenceTransformer
from services.database import execute_query
import json

# Load model once at startup (cached)
_model = None

def get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_text_for_embedding(title, deck, body, metadata):
    """Combine fields into searchable text."""
    parts = [title]
    
    if deck:
        parts.append(deck)
    
    parts.append(body)
    
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    
    if metadata.get('tags'):
        parts.extend(metadata['tags'])
    
    if metadata.get('seo_keywords'):
        parts.extend(metadata['seo_keywords'])
    
    if metadata.get('read_category'):
        parts.append(metadata['read_category'])
    
    if metadata.get('subcategory'):
        parts.append(metadata['subcategory'])
    
    return ' '.join(parts)

def regenerate_embedding(content_id: int) -> bool:
    """Regenerate embedding for a specific content block."""
    try:
        # Fetch content
        sql = """
            SELECT id, title, deck, body, metadata 
            FROM company.content_blocks
            WHERE id = %s
        """
        result = execute_query(sql, (content_id,))
        
        if not result:
            print(f"Content {content_id} not found")
            return False
        
        content = result[0]
        
        # Generate embedding
        text = generate_text_for_embedding(
            content['title'],
            content.get('deck', ''),
            content['body'],
            content['metadata']
        )
        
        model = get_model()
        embedding = model.encode(text).tolist()
        
        # Update database
        update_sql = """
            UPDATE company.content_blocks 
            SET embedding = %s::company.vector
            WHERE id = %s
        """
        execute_query(update_sql, (embedding, content_id))
        
        print(f"✓ Embedding updated for content {content_id}")
        return True
        
    except Exception as e:
        print(f"Error updating embedding for {content_id}: {e}")
        return False