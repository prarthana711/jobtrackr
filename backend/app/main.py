from fastapi import FastAPI

from app.routers import applications, auth, jobs

app = FastAPI(title="JobTrackr")

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)


@app.get("/health")
def health():
    return {"status": "ok"}