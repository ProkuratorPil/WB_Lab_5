# Лабораторный проект Web-программирование (Lab Project API)

API для лабораторных работ №2-№7 по веб-программированию.
Реализовано на **FastAPI** с **MongoDB** (Beanie ODM), **Redis** (кеширование + JTI revocation), **MinIO** (объектное хранилище), **JWT** (access + refresh токены), **OAuth 2.0** (Яндекс, VK).

## Функциональность

### Аутентификация и авторизация
- Регистрация с валидацией пароля (заглавные, строчные, цифры)
- Вход с установкой HttpOnly cookies (access_token, refresh_token)
- Refresh токенов (rotation)
- Выход из текущей и всех сессий
- OAuth 2.0 через Яндекс и VK (Authorization Code Grant)
- Soft Delete для пользователей
- Кеширование профиля в Redis

### Управление пользователями
- CRUD пользователей (Create, Read, Update, Delete)
- Кеширование списков и профилей в Redis
- Пагинация

### Файлы (MinIO Object Storage)
- **POST /files** — Загрузка файла (multipart/form-data) в MinIO с потоковой передачей
- **GET /files** — Список файлов пользователя (пагинированный)
- **GET /files/{file_id}** — Скачивание файла через StreamingResponse
- **DELETE /files/{file_id}** — Удаление файла (hard delete из MinIO + soft delete в MongoDB)
- Валидация MIME-типов и размеров файлов (10 MB макс.)
- Метаданные файлов хранятся в MongoDB, файлы — в MinIO
- Кеширование метаданных файлов в Redis (TTL: 300 сек)

### Профиль и Аватар
- **GET /users/profile** — Получение профиля текущего пользователя
- **POST /users/profile** — Обновление профиля (display_name, bio, avatar_file_id)
- Проверка владения файлом при установке аватара
- Кеширование профиля в Redis

## Технологический стек

- **FastAPI** (async Python web framework)
- **MongoDB 7** (NoSQL база данных)
- **Beanie ODM** (async MongoDB ODM)
- **Redis 7** (кеширование, JTI revocation)
- **MinIO** (объектное хранилище, S3-совместимое)
- **JWT** (access + refresh токены)
- **OAuth 2.0** (Яндекс, VK)
- **Docker** + **Docker Compose**

## Быстрый старт

### Требования

- Docker и Docker Compose
- Git

### Установка и запуск

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd WB_Lab_5

# 2. Создайте файл .env на основе .env.example
cp .env.example .env
# Отредактируйте .env при необходимости

# 3. Запустите все сервисы
docker-compose up --build
```

### Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| API | http://localhost:4200 | FastAPI приложение |
| Swagger UI | http://localhost:4200/docs | Документация API |
| ReDoc | http://localhost:4200/redoc | Альтернативная документация |
| MinIO API | http://localhost:9000 | S3-совместимый API |
| MinIO Console | http://localhost:9001 | Web-интерфейс MinIO |
| Redis Insight | http://localhost:5540 | Web-интерфейс Redis |

### MinIO Console

1. Откройте http://localhost:9001
2. Войдите с логином: `minio_admin`, пароль: `minio_secure_password`
3. Создайте bucket: `wp-labs-files` (если не создался автоматически)

## API Endpoints

### Аутентификация

| Метод | URI | Описание | Доступ |
|-------|-----|----------|--------|
| POST | /auth/register | Регистрация | Public |
| POST | /auth/login | Вход | Public |
| POST | /auth/refresh | Обновление токенов | Cookie |
| POST | /auth/logout | Выход | Private |
| POST | /auth/logout-all | Выход из всех сессий | Private |
| GET | /auth/whoami | Текущий пользователь | Private |
| GET | /auth/oauth/{provider} | OAuth авторизация | Public |
| GET | /auth/oauth/{provider}/callback | OAuth callback | Public |
| POST | /auth/forgot-password | Запрос сброса пароля | Public |
| POST | /auth/reset-password | Сброс пароля | Public |

### Пользователи

| Метод | URI | Описание | Доступ |
|-------|-----|----------|--------|
| POST | /users | Создать | Public |
| GET | /users | Список | Private |
| GET | /users/{user_id} | По ID | Private |
| PUT | /users/{user_id} | Обновить | Owner |
| PATCH | /users/{user_id} | Частичное обновление | Owner |
| DELETE | /users/{user_id} | Удалить | Owner |
| GET | /users/profile | Профиль | Own |
| POST | /users/profile | Обновить профиль | Own |

### Файлы

| Метод | URI | Описание | Статус успеха | Доступ |
|-------|-----|----------|---------------|--------|
| POST | /files | Загрузка файла (multipart/form-data) | 201 Created | Private |
| GET | /files | Список файлов | 200 OK | Owner |
| GET | /files/{file_id} | Скачивание файла | 200 OK | Owner |
| DELETE | /files/{file_id} | Удаление файла | 204 No Content | Owner |

### Системные

| Метод | URI | Описание |
|-------|-----|----------|
| GET | / | Приветствие |
| GET | /health | Healthcheck |

## Переменные окружения (.env)

```env
# MongoDB
DB_USER=student
DB_PASSWORD=student_secure_password
DB_NAME=wp_labs
MONGO_URI="mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin"

# Application
PORT=4200
NODE_ENV=development

# JWT
JWT_ACCESS_SECRET=your_access_secret_key
JWT_REFRESH_SECRET=your_refresh_secret_key
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password_change_in_prod
CACHE_TTL_DEFAULT=300

# Yandex OAuth
YANDEX_CLIENT_ID=
YANDEX_CLIENT_SECRET=
YANDEX_CALLBACK_URL=http://localhost:4200/auth/oauth/yandex/callback

# VK OAuth
VK_CLIENT_ID=
VK_CLIENT_SECRET=
VK_CALLBACK_URL=http://localhost:4200/auth/oauth/vk/callback

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_secure_password
MINIO_BUCKET=wp-labs-files
MINIO_USE_SSL=false
MAX_FILE_SIZE=10485760
```

## Архитектура

### Модульная структура

```
app/
├── api/            # Альтернативные роутеры
├── core/           # Ядро: config, database, dependencies, cache, jwt, security, oauth
├── crud/           # CRUD операции (file_crud, token_crud, book.py - user_crud)
├── models/         # Beanie ODM документы (user, token, uploaded_file)
├── routers/        # Роутеры FastAPI (auth, user, file)
├── schemas/        # Pydantic схемы (auth, common, file, user)
└── services/       # Бизнес-логика (user_service, file_service, minio_service)
```

### Поток загрузки файла (Streaming)

```
Client → POST /files (multipart/form-data)
  → FastAPI получает UploadFile
  → MinioService: потоковая загрузка (put_object)
  → MongoDB: сохранение метаданных
  → Redis: инвалидация кеша
  → Response: 201 + метаданные
```

### Поток скачивания файла (Streaming)

```
Client → GET /files/{file_id}
  → Проверка владения (file.user_id == current_user.id)
  → Redis: проверка кеша метаданных
  → MinioService: get_file_stream
  → StreamingResponse (32KB chunks)
  → Заголовки: Content-Type, Content-Disposition, Content-Length
```

## Кеширование

### Ключи Redis

- `wp:auth:user:{user_id}:access:{jti}` — JTI для мгновенного отзыва токенов
- `wp:users:detail:{user_id}` — Детали пользователя
- `wp:users:profile:{user_id}` — Профиль пользователя
- `wp:users:list:*` — Списки пользователей
- `wp:files:{file_id}:meta` — Метаданные файла
- `wp:files:list:{user_id}:*` — Списки файлов пользователя

### TTL по умолчанию: 300 секунд
### Инвалидация: при создании, обновлении, удалении

## Безопасность

- Пароли хешируются через bcrypt/pbkdf2_sha256
- Токены хранятся в HttpOnly cookies (защита от XSS)
- JTI (JWT ID) для мгновенного отзыва токенов через Redis
- Валидация MIME-типов при загрузке файлов
- Ограничение размера файлов (10 MB)
- Проверка владения файлами
- Soft Delete для пользователей и файлов
- Чувствительные данные в .env