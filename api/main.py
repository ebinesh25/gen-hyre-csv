from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.parse import router as parse_router

app = FastAPI(
    title="Hyrenet Question Library API",
    description="API for parsing DOCX question files to CSV",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router, prefix="/api", tags=["parse"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
