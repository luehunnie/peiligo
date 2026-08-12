from fastapi import FastAPI

from app.api.contents import router as contents_router

app = FastAPI(title="培黎智寻 API", version="0.1.0")

app.include_router(contents_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
