import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analytics, applications, auth, jobs, matching, reminders, resumes
from app.services.scheduler import reminder_loop

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the reminder checker in the background, if it is switched on
    task = asyncio.create_task(reminder_loop()) if settings.reminder_loop_enabled else None
    yield
    # The app is shutting down: stop the checker cleanly
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="JobTrackr", lifespan=lifespan)

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
app.include_router(reminders.router)


@app.get("/health")
def health():
    return {"status": "ok"}