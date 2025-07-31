from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.api.endpoints import efatura, bank, matching, reports
from app.core.config import settings

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Conciliador E-fatura API...")
    yield
    # Shutdown
    print("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Conciliador E-fatura API",
    description="API for reconciling e-fatura records with bank movements",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "conciliador-efatura-api"
    }

# Include routers
app.include_router(efatura.router, prefix="/api/v1/efatura", tags=["E-fatura"])
app.include_router(bank.router, prefix="/api/v1/bank", tags=["Bank"])
app.include_router(matching.router, prefix="/api/v1/matching", tags=["Matching"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Conciliador E-fatura API",
        "docs": "/docs",
        "redoc": "/redoc"
    }