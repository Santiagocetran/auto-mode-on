"""FastAPI application factory and router wiring.

⚠️ P4 owns the canonical version of this file (see roles-and-ownership.md).
This is the minimal skeleton that unblocks all four lanes — coordinate with P4
before fleshing out app-wide concerns (lifespan, middleware, error handlers).
"""

from fastapi import FastAPI

from app.routers import meetings, reminders, whatsapp


# Bump this whenever you need to confirm a deploy actually shipped new code.
# Hit GET /health on the deployed API and check the `build` field.
BUILD_MARKER = "confirmation-gate"
APP_VERSION = "0.2.0"


def create_app() -> FastAPI:
    app = FastAPI(title="Halketon API", version=APP_VERSION)

    app.include_router(whatsapp.router)
    app.include_router(reminders.router)
    app.include_router(meetings.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, object]:
        return {"ok": True, "version": APP_VERSION, "build": BUILD_MARKER}

    return app


app = create_app()
