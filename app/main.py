from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, profile, sleep_data
from app.database import engine, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database tables: {e}")
    logger.warning("Application starting without database connection. Some endpoints will fail.")

app = FastAPI(
    title="SmartSleep API",
    description="""
The SmartSleep API provides a comprehensive backend for the Personalized Sleep Quality Analyzer.

### Features
* **User Management**: Secure signup and login with JWT.
* **Data Ingestion**: Log raw sleep data, caffeine intake, and lifestyle factors.
* **Sleep Analysis**: Automatic calculation of sleep efficiency, base scores, and penalties.
* **ML Insights**: Blended scoring using machine learning (online learning ready).
* **Statistics**: Rolling averages and standard deviations using Welford's algorithm.

---
**Note**: To access protected routes, use the **Authorize** button with a JWT token obtained from the `/login` endpoint.
    """,
    version="1.0.0",
    contact={
        "name": "SmartSleep Support",
        "url": "https://github.com/yourusername/SmartSleepBackend",
    },
    license_info={
        "name": "MIT License",
    },
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(sleep_data.router, prefix="/api/v1/sleep", tags=["Sleep Data"])

@app.get("/")
def root():
    return {"message": "Welcome to SmartSleep API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
