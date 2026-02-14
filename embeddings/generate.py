from sentence_transformers import SentenceTransformer
import psycopg2

# Load model (downloads on first run, ~90MB)
print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="postgres",      # container name = hostname in docker network
    database="company_data",
    user="admin",
    password="K0l(mbin)"   # use your actual password
)
cur = conn.cursor()

# Fetch blocks without embeddings
cur.execute("""
    SELECT id, title, body 
    FROM company.content_blocks 
    WHERE embedding IS NULL
""")
rows = cur.fetchall()

print(f"Found {len(rows)} blocks to embed")

# Generate and store embeddings
for id, title, body in rows:
    text = f"{title}. {body}"
    embedding = model.encode(text).tolist()
    
    cur.execute("""
        UPDATE company.content_blocks 
        SET embedding = %s 
        WHERE id = %s
    """, (embedding, id))
    
    print(f"  Embedded: {title[:40]}...")

conn.commit()
cur.close()
conn.close()

print("Done!")