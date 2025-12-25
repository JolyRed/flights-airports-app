"""
Модуль data_loader.py - Скрипт загрузки исходных данных в базу данных.

Назначение:
    Загружает данные из файлов формата *.dat проекта OpenFlights:
    - airports.dat    → таблица airports
    - airlines.dat   → таблица airlines
    - routes.dat      → таблица routes

Особенности:
    - При каждом запуске удаляет существующую базу (если есть) и создаёт новую
    - Обрабатывает возможные ошибки в данных (пропускает некорректные строки)
    - Устанавливает связи между таблицами через ForeignKey (airline_id, source_id, dest_id)
    - Использует поиск аэропортов и авиакомпаний по кодам IATA/ICAO для корректной привязки маршрутов

Запуск:
    python data_loader.py

    Рекомендуется запускать один раз при первом развёртывании приложения.
    При повторном запуске база будет пересоздана.

Note:
    Процесс загрузки может занимать 5–15 минут в зависимости от производительности системы.
    Все операции выполняются в одной сессии SQLAlchemy для оптимальной производительности.
"""

import csv
from sqlalchemy import or_
from database import Base, engine, SessionLocal
from models import Airport, Airline, Route


def load_airports(session):
    """
    Загружает данные об аэропортах из файла data/airports.dat в таблицу airports.

    Формат строки в airports.dat (14 полей):
    0: Airport ID
    1: Name
    2: City
    3: Country
    4: IATA
    5: ICAO
    6: Latitude
    7: Longitude
    8: Altitude
    9: Timezone
    10: DST
    11: Tz database time zone
    12: Type
    13: Source

    Args:
        session (Session): Активная сессия SQLAlchemy для добавления записей

    Behavior:
        - Пропускает строки с недостаточным количеством полей
        - Обрабатывает значения "\\N" как None
        - Преобразует числовые поля с проверкой корректности
        - Добавляет объекты в сессию и коммитит в конце

    Note:
        Это первая функция загрузки — должна выполняться до load_routes(),
        так как маршруты ссылаются на аэропорты.
    """
    print("Загрузка аэропортов из airports.dat...")
    with open("data/airports.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 12 or row[0] == "\\N":
                continue
            try:
                session.add(Airport(
                    id=int(row[0]),
                    name=row[1].strip('"') if row[1] != "\\N" else "",
                    city=row[2].strip('"') if row[2] != "\\N" else "",
                    country=row[3].strip('"') if row[3] != "\\N" else "",
                    iata=row[4].strip('"') if row[4] != "\\N" else None,
                    icao=row[5].strip('"') if row[5] != "\\N" else None,
                    latitude=float(row[6]),
                    longitude=float(row[7]),
                    altitude=int(row[8]) if row[8] != "\\N" else 0,
                    timezone=float(row[9]) if row[9] != "\\N" else None,
                    dst=row[10],
                    tz=row[11],
                ))
            except Exception as e:
                # Пропускаем некорректные строки, логируем в будущем можно добавить
                continue
    session.commit()
    print("Аэропорты загружены успешно.")


def load_airlines(session):
    """
    Загружает данные об авиакомпаниях из файла data/airlines.dat в таблицу airlines.

    Формат строки в airlines.dat (8 полей):
    0: Airline ID
    1: Name
    2: Alias
    3: IATA
    4: ICAO
    5: Callsign
    6: Country
    7: Active

    Args:
        session (Session): Активная сессия SQLAlchemy для добавления записей

    Behavior:
        - Пропускает строки с недостаточным количеством полей
        - Обрабатывает значения "\\N" как None
        - Добавляет объекты в сессию и коммитит в конце

    Note:
        Должна выполняться после load_airports(), но до load_routes().
    """
    print("Загрузка авиакомпаний из airlines.dat...")
    with open("data/airlines.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 8 or row[0] == "\\N":
                continue
            session.add(Airline(
                id=int(row[0]),
                name=row[1].strip('"'),
                alias=row[2].strip('"') if row[2] != "\\N" else None,
                iata=row[3].strip('"') if row[3] != "\\N" else None,
                icao=row[4].strip('"') if row[4] != "\\N" else None,
                callsign=row[5].strip('"') if row[5] != "\\N" else None,
                country=row[6].strip('"'),
                active=row[7],
            ))
    session.commit()
    print("Авиакомпании загружены успешно.")


def load_routes(session):
    """
    Загружает данные о маршрутах из файла data/routes.dat в таблицу routes.

    Формат строки в routes.dat (9 полей):
    0: Airline (2-letter code)
    1: Airline ID
    2: Source airport code
    3: Source airport ID
    4: Destination airport code
    5: Destination airport ID
    6: Codeshare
    7: Stops
    8: Equipment

    Args:
        session (Session): Активная сессия SQLAlchemy для добавления записей

    Behavior:
        - Ищет аэропорты и авиакомпании по коду IATA или ICAO
        - Привязывает foreign keys (source_id, dest_id, airline_id)
        - Пропускает маршруты, если не найдены аэропорты отправления/прибытия
        - Устанавливает stops = 0 для прямых рейсов
        - Добавляет объекты в сессию и коммитит в конце

    Note:
        Это последняя функция загрузки — требует наличия аэропортов и авиакомпаний в БД.
        Самая ресурсоёмкая часть — может занять основное время выполнения скрипта.
    """
    print("Загрузка маршрутов из routes.dat...")
    with open("data/routes.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 9:
                continue

            # Поиск аэропорта отправления по коду
            source = session.query(Airport).filter(or_(Airport.iata == row[2], Airport.icao == row[2])).first()
            # Поиск аэропорта прибытия по коду
            dest = session.query(Airport).filter(or_(Airport.iata == row[4], Airport.icao == row[4])).first()
            # Поиск авиакомпании по коду
            airline = session.query(Airline).filter(or_(Airline.iata == row[0], Airline.icao == row[0])).first()

            if source and dest:
                session.add(Route(
                    airline_code=row[0],
                    airline_id=airline.id if airline else None,
                    source_code=row[2],
                    source_id=source.id,
                    dest_code=row[4],
                    dest_id=dest.id,
                    codeshare=row[6] if len(row) > 6 else "",
                    stops=int(row[7]) if row[7].isdigit() else 0,
                    equipment=row[8] if len(row) > 8 else "",
                ))
    session.commit()
    print("Маршруты загружены успешно.")


if __name__ == "__main__":
    """
    Точка входа скрипта при прямом запуске.

    Последовательность действий:
        1. Удаление существующей базы (если есть)
        2. Создание новой структуры таблиц
        3. Открытие сессии
        4. Последовательная загрузка: аэропорты → авиакомпании → маршруты
        5. Закрытие сессии

    Выводит прогресс в консоль.
    """
    print("Начало загрузки данных в базу...")
    Base.metadata.drop_all(bind=engine)    # Удаляем старую базу
    Base.metadata.create_all(bind=engine)  # Создаём таблицы

    db = SessionLocal()
    try:
        load_airports(db)
        load_airlines(db)
        load_routes(db)
    finally:
        db.close()

    print("Загрузка данных завершена успешно! База database.db готова к использованию.")