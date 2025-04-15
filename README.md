# Posts Analyzer API

Асинхронный сервис для фильтрации и анализа текстовых постов с использованием FastAPI и SQLAlchemy.

## Функциональность

- Фильтрация постов по категории и ключевым словам
- Полнотекстовый поиск на базе PostgreSQL
- Асинхронная обработка данных
- Пагинация с метаданными
- Оптимизированная пакетная обработка
- Анализ текста (частота слов, статистика, теги)

## Технологии

- Python 3.11
- FastAPI
- SQLAlchemy 2.0 (асинхронный режим)
- PostgreSQL
- Alembic (миграции)
- Docker & Docker Compose
- NLTK (анализ текста)

## Структура проекта

```
posts-analyzer/
│
├── .env                      # Переменные окружения
├── docker-compose.yml        # Docker Compose конфигурация
├── Dockerfile                # Docker образ
├── requirements.txt          # Зависимости
├── alembic.ini               # Конфигурация Alembic
│
└── src/                      # Исходный код
    ├── alembic/              # Миграции базы данных
    ├── api/                  # API эндпоинты
    ├── core/                 # Ядро приложения
    ├── db/                   # Модели и CRUD операции
    ├── schemas/              # Pydantic схемы
    ├── services/             # Бизнес-логика
    └── main.py               # Точка входа
```

## Установка и запуск

### Локальное окружение

1. Клонировать репозиторий:
   ```bash
   git clone <repository-url>
   cd posts-analyzer
   ```

2. Создать виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # для Linux/macOS
   # или
   venv\Scripts\activate     # для Windows
   ```

3. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Настроить переменные окружения в файле `.env`

5. Запустить миграции:
   ```bash
   alembic upgrade head
   ```

6. Запустить приложение:
   ```bash
   python -m src.main
   ```

### Docker Compose

1. Клонировать репозиторий:
   ```bash
   git clone <repository-url>
   cd posts-analyzer
   ```

2. Настроить переменные окружения в файле `.env`

3. Запустить с Docker Compose:
   ```bash
   docker-compose up -d
   ```

## API Endpoints

### Posts

- `GET /api/v1/posts` - Получить посты с фильтрацией и пагинацией
- `GET /api/v1/posts/{post_id}` - Получить пост по ID
- `POST /api/v1/posts/` - Создать новый пост
- `PUT /api/v1/posts/{post_id}` - Обновить существующий пост
- `DELETE /api/v1/posts/{post_id}` - Удалить пост

### Categories

- `GET /api/v1/posts/categories/{category_id}` - Получить категорию по ID
- `POST /api/v1/posts/categories/` - Создать новую категорию
- `PUT /api/v1/posts/categories/{category_id}` - Обновить существующую категорию
- `DELETE /api/v1/posts/categories/{category_id}` - Удалить категорию

### Analytics

- `GET /api/v1/posts/{post_id}/analyze` - Анализировать пост
- `POST /api/v1/posts/analyze` - Анализировать посты по фильтру

## Документация API

После запуска API доступна документация Swagger:
- `http://localhost:8000/api/docs`
- `http://localhost:8000/api/redoc`