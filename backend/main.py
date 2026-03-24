from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes.auth import router as auth_router
from app.routes.slots import router as slots_router
from app.routes.reservations import router as reservations_router
from app.routes.transactions import router as transactions_router
from app.routes.competitions import router as competitions_router
from app.routes.auctions import router as auctions_router
from app.routes.notifications import router as notifications_router
from app.routes.dashboard import router as dashboard_router
from app.routes.mock import router as mock_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Panama Canal Enhanced Booking System",
    description="Full-stack booking system for the Panama Canal Authority",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(auth_router)
app.include_router(slots_router)
app.include_router(reservations_router)
app.include_router(transactions_router)
app.include_router(competitions_router)
app.include_router(auctions_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(mock_router)

@app.get("/")
def root():
    return {
        "name": "Panama Canal Enhanced Booking System",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
