from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

from app import claude, origin, recap, runs, trace

app = FastAPI(title="Utty's lab API")


@app.middleware("http")
async def only_via_cloudfront(request: Request, call_next):
    """Refuses requests that didn't come through CloudFront, so the site password can't be skipped."""
    if not origin.from_cloudfront(request.headers.get(origin.HEADER)):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def no_store(request: Request, call_next):
    """Answers are made fresh for each request, so browsers mustn't keep a copy."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/hello")
def hello():
    return {"message": "Hello World"}


@app.get("/api/hello-claude")
def hello_claude():
    """A first call to Claude: proves the key, the SDK and the network path all work."""
    try:
        message = claude.ask(
            system="You are greeting visitors to Utty's lab, a small site of AI experiments. Be warm and brief.",
            prompt="Say hello in one short, cheerful sentence.",
        )
    except claude.ClaudeUnavailable as e:
        return JSONResponse({"detail": str(e)}, status_code=503)
    return {"message": message, "model": claude.MODEL}


@app.post("/api/runs", dependencies=[Depends(runs.import_key_matches)])
def import_runs(batch: runs.RunBatch):
    """Adds runs sent by scripts/import-runs.py --send; runs already here are skipped, so re-importing is safe."""
    added = sum(runs.add(run) for run in batch.runs)
    return {"added": added, "already_had": len(batch.runs) - added}


@app.get("/api/runs")
def list_runs():
    return {"runs": runs.all_runs()}


@app.get("/api/recap")
def run_recap(start: str | None = None):
    """Minnie and Maverick review one run (by its start time), or the latest run. The run's newest saved recap is
    reused, so each run costs one Claude call; a new one is saved with the trace of every step that wrote it."""
    with trace.start("Recap") as recap_trace:
        with trace.step("Fetch the run", "data") as span:
            if start:
                run = runs.get(start)
            else:
                latest = runs.all_runs()
                run = latest[0] if latest else None
            span.note = "Distance, time, splits and heart rate, from the runs table"
        if run is None:
            return JSONResponse({"detail": "No such run"}, status_code=404)
        saved = recap.latest(run.start)
        if saved:
            return {"run": run} | saved.model_dump()
        try:
            run_facts, review = recap.write(run)
        except claude.ClaudeUnavailable as e:
            return JSONResponse({"detail": str(e)}, status_code=503)
    # Saved once the trace has ended, so its timings cover the whole request.
    return {"run": run} | recap.save(run, run_facts, review, recap_trace).model_dump()


# Entry point for AWS Lambda (API Gateway HTTP API events -> ASGI).
handler = Mangum(app, lifespan="off")
