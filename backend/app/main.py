from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

from app import claude, origin

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


# Entry point for AWS Lambda (API Gateway HTTP API events -> ASGI).
handler = Mangum(app, lifespan="off")
