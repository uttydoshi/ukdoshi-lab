from fastapi import FastAPI, Request
from mangum import Mangum

app = FastAPI(title="Utty's lab API")


@app.middleware("http")
async def no_store(request: Request, call_next):
    """Answers are made fresh for each request, so browsers mustn't keep a copy."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/hello")
def hello():
    return {"message": "Hello World"}


# Entry point for AWS Lambda (API Gateway HTTP API events -> ASGI).
handler = Mangum(app, lifespan="off")
