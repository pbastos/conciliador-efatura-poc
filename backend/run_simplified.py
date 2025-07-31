#!/usr/bin/env python3
"""
Simple runner for the Conciliador E-fatura POC
"""
import uvicorn

if __name__ == "__main__":
    print("Starting Conciliador E-fatura POC...")
    print("API will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Database: conciliador.db (will be created automatically)")
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(
        "app.main_simplified:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )