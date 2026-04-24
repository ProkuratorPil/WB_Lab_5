# main_fastapi.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import logging
import os

from app.routers import user_router
from app.routers import file_router
from app.routers.auth_router import router as auth_router
from app.core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определяем окружение
IS_PRODUCTION = os.getenv('NODE_ENV') == 'production'

# Конфигурация OAuth для Swagger UI (только в dev)
swagger_ui_oauth = None
if not IS_PRODUCTION:
    swagger_ui_oauth = {
        "clientId": settings.YANDEX_CLIENT_ID,
        "clientSecret": settings.YANDEX_CLIENT_SECRET,
        "scopes": ["login:email", "login:info"],
        "appName": "Lab Project API",
        "usePkceWithAuthorizationCodeGrant": True,
    }

# В production отключаем документацию
app = FastAPI(
    title="Lab Project API",
    description="Документация API для лабораторных работ №2-№4",
    version="1.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
    swagger_ui_init_oauth=swagger_ui_oauth,
)

# Кастомная OpenAPI схема с настройками безопасности (только в dev)
if not IS_PRODUCTION:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Lab Project API",
            version="1.0",
            description="Документация API для лабораторных работ №2-№4",
            routes=app.routes,
        )
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT токен, получаемый после авторизации. Также поддерживается передача через Cookie."
            },
            "cookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "access_token",
                "description": "JWT токен доступа, хранящийся в HttpOnly cookie"
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://oauth.yandex.ru/authorize",
                        "tokenUrl": "https://oauth.yandex.ru/token",
                        "scopes": {
                            "login:email": "Доступ к email пользователя",
                            "login:info": "Доступ к информации о профиле"
                        }
                    }
                },
                "description": "OAuth 2.0 авторизация через Яндекс"
            }
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

# Кастомный ReDoc с рабочим CDN (только в dev)
if not IS_PRODUCTION:
    from fastapi.responses import HTMLResponse

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return HTMLResponse(
            """
            <!DOCTYPE html>
            <html>
            <head>
            <title>Lab Project API - ReDoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>body { margin: 0; padding: 0; }</style>
            </head>
            <body>
            <noscript>ReDoc requires Javascript to function. Please enable it to browse the documentation.</noscript>
            <redoc spec-url="/openapi.json"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
            </body>
            </html>
            """
        )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Глобальная обработка исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик ошибок."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Подключение роутеров
app.include_router(auth_router)
app.include_router(user_router.router)
app.include_router(file_router.router)


@app.get("/", tags=["System"])
def read_root():
    return {"message": "Welcome to the Lab Project API"}


@app.get("/health", tags=["System"], summary="Проверка работоспособности")
def health_check():
    """Healthcheck endpoint."""
    return {"status": "healthy"}
