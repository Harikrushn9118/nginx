from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import asyncpg
import hashlib
import hmac
import json
import time
import base64
import struct

app = FastAPI()
INSTANCE = os.getenv("INSTANCE_ID", "1")
DB_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "demo-secret")

def verify_jwt(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    parts = token.split(".")
    if len(parts) != 3:
        return None

    header, payload, signature = parts

    expected_sig = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
    if signature != expected_sig:
        return None

    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding

    try:
        data = json.loads(base64.urlsafe_b64decode(payload).decode())
    except Exception:
        return None

    if data.get("exp", 0) < int(time.time()):
        return None

    return data

def text_to_vector(text: str, dim: int=128) -> list:
    vector = [0.0]*dim
    words = text.lower().split()
    for word in words:
        h = hashlib.md5(word.encode()).digest()
        for i in range(0, len(h), 2):
            idx = h[i] % dim
            val = struct.unpack('b', bytes([h[i+1]]))[0] / 127.0
            vector[idx] += val
    magnitude = sum(v*v for v in vector) ** 0.5
    if magnitude>0:
        vector = [v/magnitude for v in vector]
    return vector

async def get_db(): 
    return await asyncpg.connect(DB_URL)

@app.post("/api/posts")
async def create_post(request: Request):
    print(f"[POST-{INSTANCE}] POST /api/posts")
    user = verify_jwt(request)
    if not user:
        return JSONResponse(status_code=401, content={"message": "Login required"})

    try:
        body = await request.json()
        content = body.get("content", "").strip()

        if not content:
            return JSONResponse(status_code=400, content={"message": "content required"})

        user_id = user["user_id"]
        embedding = text_to_vector(content)
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        conn = await get_db()
        try:
            post = await conn.fetchrow(
                "INSERT INTO posts (user_id, content, embedding) VALUES ($1, $2, $3::vector) RETURNING id, created_at",
                user_id, content, embedding_str
            )
            return {"message": "post created", "post_id": post["id"], "created_at": str(post["created_at"]), "instance": INSTANCE}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/posts")
async def get_feed():
    print(f"[POST-{INSTANCE}] GET /api/posts")
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT p.id, p.content, p.likes, p.created_at, u.username
            FROM posts p JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC LIMIT 50
        """)
        posts = [{"id": r["id"], "content": r["content"], "likes": r["likes"], "created_at": str(r["created_at"]), "username": r["username"]} for r in rows]
        return {"posts": posts, "count": len(posts), "instance": INSTANCE}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await conn.close()

@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, request: Request):
    print(f"[POST-{INSTANCE}] POST /api/posts/{post_id}/like")
    user = verify_jwt(request)
    if not user:
        return JSONResponse(status_code=401, content={"message": "Login required"})

    try:
        user_id = user["user_id"]
        conn = await get_db()
        try:
            existing = await conn.fetchrow("SELECT id FROM post_likes WHERE post_id = $1 AND user_id = $2", post_id, user_id)

            if existing:
                return JSONResponse(status_code=409, content={"message": "already liked"})

            await conn.execute("INSERT INTO post_likes (post_id, user_id) VALUES ($1, $2)", post_id, user_id)
            await conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = $1", post_id)
            return {"message": "post liked", "instance": INSTANCE}
        finally:
            await conn.close()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/posts/health")
async def health():
    return {"service": "POST", "instance": INSTANCE, "status": "ok"}
