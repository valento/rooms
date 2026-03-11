import sys
import psycopg2
from sentence_transformers import SentenceTransformer
import os

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_text_for_embedding(title, deck, body, metadata):
    """Combine title, deck, body, and metadata into searchable text."""
    parts = [title]
    
    if deck:
        parts.append(deck)
    
    parts.append(body)
    
    if 'tags' in metadata:
        parts.extend(metadata['tags'])
    
    if 'seo_keywords' in metadata:
        parts.extend(metadata['seo_keywords'])
    
    if 'read_category' in metadata:
        parts.append(metadata['read_category'])
    if 'subcategory' in metadata:
        parts.append(metadata['subcategory'])
    
    return ' '.join(parts)

def update_embedding(content_id):
    """Update embedding for a single content block."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=5432,
        database=os.getenv("POSTGRES_DB", "company_data"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    
    cur = conn.cursor()
    
    # Fetch content
    cur.execute("""
        SELECT id, title, deck, body, metadata 
        FROM company.content_blocks
        WHERE id = %s
    """, (content_id,))
    
    row = cur.fetchone()
    
    if not row:
        print(f"Content {content_id} not found")
        return False
    
    content_id, title, deck, body, metadata = row
    
    # Generate embedding
    text = generate_text_for_embedding(title, deck, body, metadata)
    embedding = model.encode(text).tolist()
    
    # Update database
    cur.execute("""
        UPDATE company.content_blocks 
        SET embedding = %s::vector
        WHERE id = %s
    """, (embedding, content_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✓ Updated embedding for content {content_id}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_single_embedding.py <content_id>")
        sys.exit(1)
    
    content_id = int(sys.argv[1])
    success = update_embedding(content_id)
    sys.exit(0 if success else 1)