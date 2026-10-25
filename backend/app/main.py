from fastapi import FastAPI

from app.routers import analytics, applications, auth, jobs, matching, resumes

app = FastAPI(title="JobTrackr")

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(resumes.router)
app.include_router(matching.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok"}