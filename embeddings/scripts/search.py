from sentence_transformers import SentenceTransformer
import psycopg2

model = SentenceTransformer('all-MiniLM-L6-v2')

# Embed user question
question = "Can you build an online store for me?"
q_embedding = model.encode(question).tolist()

conn = psycopg2.connect(host="postgres", database="company_data", user="admin", password="changeme")
cur = conn.cursor()

cur.execute("""
    SET search_path TO company, public;
    SELECT title, body, embedding <=> %s::vector AS distance
    FROM content_blocks
    ORDER BY distance
    LIMIT 3
""", (q_embedding,))

for title, body, distance in cur.fetchall():
    print(f"{distance:.3f} | {title}")
    print(f"        {body[:60]}...")
    print()