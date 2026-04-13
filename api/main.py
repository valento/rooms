from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from services.database import get_db_connection
from routers import search, content, auth, categories, apps, toto2, polls

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://cleotilde-ectogenetic-viscidly.ngrok-free.dev",
    ],  # In production, specify your React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router)
app.include_router(content.router)
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(apps.router)
app.include_router(toto2.router)
app.include_router(polls.router)

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Company Search API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "service": "FastAPI Search API"
        }
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")