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

def create_jwt(user_id: int, username: str):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + 86400  
    }).encode()).decode().rstrip("=")
    signature = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"{header}.{payload}.{signature}"

def hash_password(password: str) -> str:
    salt = "fixed-salt-for-demo"
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()

async def get_db():
    return await asyncpg.connect(DB_URL)

@app.post("/auth/register")
async def register(request: Request):
    print(f"🔐 [AUTH-{INSTANCE}] POST /auth/register")
    try:
        body = await request.json()
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()
        email = body.get("email", "").strip()

        if not username or not password:
            return JSONResponse(status_code=400, content={"message": "username and password required"})

        conn = await get_db()
        try:
            existing = await conn.fetchrow("SELECT id FROM users WHERE username = $1", username)
            if existing:
                return JSONResponse(status_code=409, content={"message": "username already taken"})

            password_hash = hash_password(password)
            user = await conn.fetchrow(
                "INSERT INTO users (username, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
                username, email, password_hash
            )
            token = create_jwt(user["id"], username)
            return {"message": "registered", "token": token, "user_id": user["id"], "instance": INSTANCE}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/auth/login")
async def login(request: Request):
    print(f"🔐 [AUTH-{INSTANCE}] POST /auth/login")
    try:
        body = await request.json()
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()

        if not username or not password:
            return JSONResponse(status_code=400, content={"message": "username and password required"})

        conn = await get_db()
        try:
            user = await conn.fetchrow("SELECT id, username, password_hash FROM users WHERE username = $1", username)
            if not user:
                return JSONResponse(status_code=401, content={"message": "invalid credentials"})

            if user["password_hash"] != hash_password(password):
                return JSONResponse(status_code=401, content={"message": "invalid credentials"})

            token = create_jwt(user["id"], user["username"])
            return {"message": "login successful", "token": token, "user_id": user["id"], "instance": INSTANCE}
        finally:
            await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/auth/health")
async def health():
    return {"service": "AUTH", "instance": INSTANCE, "status": "ok"}
