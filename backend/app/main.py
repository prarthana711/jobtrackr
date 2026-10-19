from fastapi import FastAPI

app = FastAPI(title="JobTrackr")


@app.get("/health")
def health():
    return {"status": "ok"}