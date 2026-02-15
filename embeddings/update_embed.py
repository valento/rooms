import os
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
import json

# Database connection
conn = psycopg2.connect(
    host="postgres",  # or "postgres" if running inside container
    port=5432,
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_text_for_embedding(title, body, metadata):
    """Combine title, body, and metadata into searchable text."""
    parts = [title, body]
    
    # Add tags
    if 'tags' in metadata:
        parts.extend(metadata['tags'])
    
    # Add seo_keywords
    if 'seo_keywords' in metadata:
        parts.extend(metadata['seo_keywords'])
    
    # Add category info
    if 'read_category' in metadata:
        parts.append(metadata['read_category'])
    if 'subcategory' in metadata:
        parts.append(metadata['subcategory'])
    
    # Join all parts
    return ' '.join(parts)

# Fetch all content blocks
cur = conn.cursor()
cur.execute("""
    SELECT id, title, body, metadata 
    FROM company.content_blocks
""")

rows = cur.fetchall()

print(f"Found {len(rows)} content blocks to update...")

# Update embeddings
for row in rows:
    content_id, title, body, metadata = row
    
    # Generate text including metadata
    text = generate_text_for_embedding(title, body, metadata)
    
    print(f"\nID {content_id}: {title}")
    print(f"  Text to embed: {text[:100]}...")
    
    # Generate embedding
    embedding = model.encode(text).tolist()
    
    # Update database
    cur.execute("""
        UPDATE company.content_blocks 
        SET embedding = %s::company.vector
        WHERE id = %s
    """, (embedding, content_id))
    
    print(f"  ✓ Embedding updated ({len(embedding)} dimensions)")

conn.commit()
cur.close()
conn.close()

print("\n✅ All embeddings updated successfully!")