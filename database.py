"""
Модуль database.py - Конфигурация подключения к базе данных SQLite.

Назначение:
    Настраивает подключение к локальной базе данных SQLite с использованием SQLAlchemy.
    Создаёт:
        - engine: объект для взаимодействия с базой
        - SessionLocal: фабрику сессий для работы в контексте запросов
        - Base: базовый класс для декларативного определения моделей (таблиц)

Особенности:
    - Используется относительный путь к файлу базы: ./database.db
    - Параметр connect_args={"check_same_thread": False} необходим для корректной работы
      SQLite в многопоточной среде FastAPI (увеличивает производительность)
    - sessionmaker настроен с autocommit=False и autoflush=False для явного контроля транзакций

Использование:
    Импортируется в других модулях:
        from database import SessionLocal, Base, engine

    Пример создания таблиц:
        Base.metadata.create_all(bind=engine)

    Пример получения сессии (в FastAPI):
        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

Note:
    Этот модуль не содержит логики приложения — только конфигурацию БД.
    База данных создаётся автоматически при первом запуске data_loader.py.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL подключения к базе данных SQLite
# Файл database.db будет создан в корневой папке проекта
SQLITE_DATABASE_URL = "sqlite:///./database.db"

# Создание engine — основного объекта для взаимодействия с БД
# connect_args={"check_same_thread": False} — отключает проверку потока для SQLite
# Это безопасно и необходимо при использовании в асинхронном/многопоточном FastAPI
engine = create_engine(
    SQLITE_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Фабрика сессий
# autocommit=False — изменения подтверждаются вручную (db.commit())
# autoflush=False — изменения не отправляются в БД автоматически при запросах
# bind=engine — привязка к созданному engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей (таблиц)
# Все модели (Airport, Airline, Route) наследуются от Base
# Используется для декларативного объявления таблиц
Base = declarative_base()