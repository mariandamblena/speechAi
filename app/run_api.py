"""
Servidor API usando FastAPI
"""

import uvicorn

def run_api():
    """Ejecuta el servidor API"""
    print("🚀 Starting Speech AI Call Tracking API")
    print("=" * 50)
    print("API Endpoints:")
    print("• Health Check: http://localhost:8000/health")
    print("• API Docs: http://localhost:8000/docs")
    print("• Alternative Docs: http://localhost:8000/redoc")
    print("=" * 50)
    
    # Ejecutar servidor
    uvicorn.run(
        "api:app",  # Usar string path en lugar del objeto importado
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    run_api()