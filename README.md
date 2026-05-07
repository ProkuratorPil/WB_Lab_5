# Lab Project API

Веб-приложение на FastAPI с аутентификацией (JWT + OAuth), кешированием (Redis) и документированием (Swagger).

## Технологический стек

- **Язык**: Python 3.12
- **Фреймворк**: FastAPI
- **База данных**: MongoDB 7 (через Beanie ODM)
- **Кеширование**: Redis 7
- **Аутентификация**: JWT (access + refresh токены), OAuth 2.0 (Яндекс, VK)
- **Документация**: Swagger UI, ReDoc
- **Контейнеризация**: Docker, Docker Compose

## Структура проекта

```
├── app/
│   ├── api/               # API роутеры (альтернативные)
│   ├── core/
│   │   ├── cache.py       # Сервис кеширования Redis
│   │   ├── config.py      # Конфигурация приложения
│   │   ├── database.py    # Подключение к MongoDB (Motor + Beanie)
│   │   ├── dependencies.py # FastAPI зависимости
│   │   ├── jwt.py         # JWT токены
│   │   ├── security.py    # Хеширование паролей/токенов
│   │   └── oauth/         # OAuth провайдеры
│   ├── crud/              # CRUD операции (async, Beanie)
│   ├── models/            # Документы MongoDB (Beanie)
│   ├── routers/           # API роутеры (async)
│   ├── schemas/           # Pydantic схемы (DTO)
│   └── services/          # Бизнес-логика (async)
├── docker-compose.yml     # Инфраструктура (MongoDB, Redis, App)
├── Dockerfile             # Сборка приложения
├── requirements.txt       # Зависимости Python
├── .env.example           # Пример переменных окружения
└── main.py                # Точка входа
```

## Запуск через Docker Compose

```bash
# Клонировать репозиторий
git clone <repository-url>
cd WB_Lab_5

# Создать .env файл из примера
cp .env.example .env
# Отредактировать .env при необходимости

# Запустить приложение
docker-compose up --build

# Приложение будет доступно по адресу:
# http://localhost:4200
# Swagger UI: http://localhost:4200/docs
```

## Переменные окружения (.env)

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|----------------------|
| `MONGO_URI` | URI подключения к MongoDB | `mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin` |
| `DB_USER` | Имя пользователя MongoDB | `student` |
| `DB_PASSWORD` | Пароль MongoDB | `student_secure_password` |
| `DB_NAME` | Название базы данных | `wp_labs` |
| `PORT` | Порт приложения | `4200` |
| `NODE_ENV` | Окружение | `development` |
| `JWT_ACCESS_SECRET` | Секрет для access токенов | — |
| `JWT_REFRESH_SECRET` | Секрет для refresh токенов | — |
| `JWT_ACCESS_EXPIRATION` | Время жизни access токена | `15m` |
| `JWT_REFRESH_EXPIRATION` | Время жизни refresh токена | `7d` |
| `REDIS_HOST` | Хост Redis | `redis` |
| `REDIS_PORT` | Порт Redis | `6379` |
| `REDIS_PASSWORD` | Пароль Redis | — |
| `CACHE_TTL_DEFAULT` | TTL кеша по умолчанию (сек) | `300` |
| `YANDEX_CLIENT_ID` | OAuth Client ID Яндекса | — |
| `YANDEX_CLIENT_SECRET` | OAuth Client Secret Яндекса | — |
| `VK_CLIENT_ID` | OAuth Client ID VK | — |
| `VK_CLIENT_SECRET` | OAuth Client Secret VK | — |

## API Эндпоинты

### Аутентификация (`/auth`)

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST | `/auth/register` | Регистрация нового пользователя | Public |
| POST | `/auth/login` | Вход в систему | Public |
| POST | `/auth/refresh` | Обновление токенов | Cookie |
| POST | `/auth/logout` | Выход из системы | Private |
| POST | `/auth/logout-all` | Выход из всех сессий | Private |
| GET | `/auth/whoami` | Информация о текущем пользователе | Private |
| GET | `/auth/oauth/{provider}` | OAuth авторизация (yandex/vk) | Public |
| GET | `/auth/oauth/{provider}/callback` | Callback OAuth | Public |
| POST | `/auth/forgot-password` | Запрос сброса пароля | Public |
| POST | `/auth/reset-password` | Сброс пароля | Public |

### Пользователи (`/users`)

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST | `/users/` | Создание пользователя | Public |
| GET | `/users/` | Список пользователей (пагинация) | Private |
| GET | `/users/{id}` | Получить пользователя по ID | Private |
| PUT | `/users/{id}` | Полное обновление пользователя | Private (владелец) |
| PATCH | `/users/{id}` | Частичное обновление пользователя | Private (владелец) |
| DELETE | `/users/{id}` | Мягкое удаление пользователя | Private (владелец) |

### Файлы (`/files`)

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST | `/files/` | Создание записи о файле | Private |
| GET | `/files/` | Список файлов (пагинация) | Private |
| GET | `/files/{id}` | Получить файл по ID | Private (владелец) |
| PUT | `/files/{id}` | Полное обновление файла | Private (владелец) |
| PATCH | `/files/{id}` | Частичное обновление файла | Private (владелец) |
| DELETE | `/files/{id}` | Мягкое удаление файла | Private (владелец) |

### Системные

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Приветственное сообщение |
| GET | `/health` | Проверка работоспособности |

## Особенности реализации

### Миграция с PostgreSQL на MongoDB

- **ORM/ODM**: SQLAlchemy → Beanie (асинхронный ODM для MongoDB)
- **Драйвер**: asyncpg/pg8000 → Motor (асинхронный драйвер MongoDB)
- **Модели**: Таблицы → Документы с UUID в качестве `_id`
- **CRUD**: Синхронные запросы → Асинхронные с Beanie
- **Роутеры**: Синхронные → Асинхронные (async/await)
- **Транзакции**: Не используются (MongoDB поддерживает транзакции в репликах)

### Кеширование (Redis)

- Паттерн Cache-Aside для списков и деталей
- JTI access токенов для мгновенного отзыва
- Инвалидация кеша при изменениях данных
- Graceful degradation при недоступности Redis

### Мягкое удаление (Soft Delete)

- Поле `deleted_at` у документов User и UploadedFile
- Автоматическая фильтрация удаленных записей в запросах
- Возможность восстановления данных

### Аутентификация

- JWT access (15 мин) + refresh (7 дней) токены
- HttpOnly cookies + Bearer токены (Header)
- Мгновенный отзыв через Redis (JTI)
- Множественные сессии для одного пользователя
- Поддержка OAuth 2.0 (Яндекс, VK)