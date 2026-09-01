from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import asyncpg
import hashlib
import hmac
import json
import time
import base64

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

async def get_db():
    return await asyncpg.connect(DB_URL)

@app.get("/api/users/health")
async def health():
    return {"service": "USER", "instance": INSTANCE, "status": "ok"}

@app.get("/api/users")
async def list_users():
    print(f"[USER-{INSTANCE}] GET /api/users")
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT id, username, email, bio, created_at FROM users ORDER BY created_at DESC LIMIT 50")
        users = [{"id": r["id"], "username": r["username"], "email": r["email"], "bio": r["bio"], "created_at": str(r["created_at"])} for r in rows]
        return {"users": users, "count": len(users), "instance": INSTANCE}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await conn.close()

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    print(f"[USER-{INSTANCE}] GET /api/users/{user_id}")
    conn = await get_db()
    try:
        user = await conn.fetchrow("SELECT id, username, email, bio, created_at FROM users WHERE id = $1", user_id)
        if not user:
            return JSONResponse(status_code=404, content={"message": "user not found"})

        post_count = await conn.fetchval("SELECT COUNT(*) FROM posts WHERE user_id = $1", user_id)
        return {
            "user": {"id": user["id"], "username": user["username"], "email": user["email"], "bio": user["bio"], "created_at": str(user["created_at"]), "post_count": post_count},
            "instance": INSTANCE
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        await conn.close()

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    print(f"[USER-{INSTANCE}] PUT /api/users/{user_id}")
    logged_in_user = verify_jwt(request)
    if not logged_in_user:
        return JSONResponse(status_code=401, content={"message": "Login required"})

    if logged_in_user["user_id"] != user_id:
        return JSONResponse(status_code=403, content={"message": "You can only edit your own profile"})

    try:
        body = await request.json()
        bio = body.get("bio", "")
        email = body.get("email", "")

        conn = await get_db()
        try:
            result = await conn.execute("UPDATE users SET bio = $1, email = $2 WHERE id = $3", bio, email, user_id)
            if result == "UPDATE 0":
                return JSONResponse(status_code=404, content={"message": "user not found"})
            return {"message": "profile updated", "instance": INSTANCE}
        finally:
            await conn.close()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
