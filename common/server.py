import uvicorn


def run_app(app, port: int) -> None:
    uvicorn.run(app, host="0.0.0.0", port=port)
