from fastapi import APIRouter
from sqlalchemy import text
from loguru import logger
from sentinel.storage.run_store import SessionLocal

router = APIRouter()

@router.get("/")
def health_check():
    """Verify backend and database connectivities."""
    logger.info("API Request: health_check")
    status = {"status": "ok", "database": "disconnected"}
    
    db = SessionLocal()
    try:
        # Execute a raw fast connect
        db.execute(text("SELECT 1"))
        status["database"] = "connected"
    except Exception as e:
        logger.error(f"Health check DB failure: {e}")
        status["error"] = str(e)
    finally:
        db.close()
        
    return status
