from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import asyncpg
import hashlib
import struct

app = FastAPI()

INSTANCE = os.getenv("INSTANCE_ID", "1")
DB_URL = os.getenv("DATABASE_URL")

def text_to_vector(text: str, dim: int = 128) -> list:
    """Convert text to a simple vector using hash-based embedding."""
    vector = [0.0] * dim
    words = text.lower().split()
    for word in words:
        h = hashlib.md5(word.encode()).digest()
        for i in range(0, len(h), 2):
            idx = h[i] % dim
            val = struct.unpack('b', bytes([h[i+1]]))[0] / 127.0
            vector[idx] += val
    magnitude = sum(v * v for v in vector) ** 0.5
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    return vector

async def get_db():
    return await asyncpg.connect(DB_URL)

@app.get("/search/posts")
async def search_posts(q: str = ""):
    print(f"🔍 [SEARCH-{INSTANCE}] GET /search/posts?q={q}")
    q = q.strip()
    if not q:
        return {"message": "provide a search query", "instance": INSTANCE}

    query_vector = text_to_vector(q)
    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT p.id, p.content, p.likes, p.created_at, u.username,
                   (p.embedding <=> $1::vector) AS distance
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE p.embedding IS NOT NULL
            ORDER BY p.embedding <=> $1::vector
            LIMIT 20
        """, vector_str)

        results = [{
            "id": r["id"],
            "content": r["content"],
            "likes": r["likes"],
            "username": r["username"],
            "similarity": round(1 - float(r["distance"]), 4),
            "created_at": str(r["created_at"])
        } for r in rows]

        return {"results": results, "count": len(results), "query": q, "instance": INSTANCE}
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await conn.close()

@app.get("/search/health")
async def health():
    return {"service": "SEARCH", "instance": INSTANCE, "status": "ok"}
