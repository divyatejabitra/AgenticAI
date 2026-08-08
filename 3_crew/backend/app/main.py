from pathlib import Path

from dotenv import load_dotenv

# Repo-root .env holds shared keys (OPENAI_API_KEY, SERPER_API_KEY, RESEND_API_KEY, ...).
# Loaded explicitly (rather than relying on a library importing it as a side effect) so
# this backend always picks it up regardless of which crew modules get imported.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routers import chat, decide, research, search, track, trending, watchlist

app = FastAPI(
    title="Borderless API",
    description="Live backend wiring the financial_researcher and stock_picker crews to the Borderless prototype",
)

# Local dev prototype only — tighten allow_origins before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trending.router, prefix="/api", tags=["discover"])
app.include_router(decide.router, prefix="/api", tags=["decide"])
app.include_router(watchlist.router, prefix="/api", tags=["watchlist"])
app.include_router(research.router, prefix="/api", tags=["stock-detail"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(track.router, prefix="/api", tags=["track"])
app.include_router(search.router, prefix="/api", tags=["stock-detail"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serves the wired Borderless frontend same-origin so its fetch() calls need no CORS.
# no-store so a normal reload always gets the latest JS instead of a cached/bfcached
# copy of the page silently running stale logic.
FRONTEND_INDEX = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def frontend_index():
    return FileResponse(
        FRONTEND_INDEX,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )
