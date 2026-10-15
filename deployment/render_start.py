"""Render provides its public URL and PORT at runtime."""
import os
import uvicorn

if os.getenv("RENDER_EXTERNAL_URL"):
    os.environ.setdefault("DEPBRIDGE_PUBLIC_BASE_URL", os.environ["RENDER_EXTERNAL_URL"])
os.environ.setdefault("DEPBRIDGE_DATA_DIR", "/tmp/depbridge-data")
os.environ.setdefault("DEPBRIDGE_FRONTEND_DIR", "/app/demo_frontend")

if __name__ == "__main__":
    uvicorn.run("depbridge_service.app:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "10000")), workers=1,
                proxy_headers=True, forwarded_allow_ips="*")
