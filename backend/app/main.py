from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analytics, applications, auth, jobs, matching, resumes

app = FastAPI(title="JobTrackr")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(resumes.router)
app.include_router(matching.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok"}