"""
Модуль crud.py - CRUD операции для работы с базой данных.

Содержит функции для выполнения операций чтения (Read) из базы данных:
- Поиск аэропортов по координатам
- Поиск аэропортов по городу и стране
- Поиск рейсов в/из города
- Поиск прямых рейсов между городами
- Поиск рейсов с одной стыковкой
- Получение уникальных городов и стран для автокомплита
"""

from sqlalchemy.orm import Session
from models import Airport, Route, Airline
from sqlalchemy import and_


def get_airports_in_coords(db: Session, lat_min: float, lat_max: float, 
                          lon_min: float, lon_max: float, 
                          page: int = 1, per_page: int = 25):
    """
    Поиск аэропортов в заданном диапазоне географических координат.
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
        lat_min (float): Минимальная широта диапазона поиска
        lat_max (float): Максимальная широта диапазона поиска
        lon_min (float): Минимальная долгота диапазона поиска
        lon_max (float): Максимальная долгота диапазона поиска
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        per_page (int, optional): Количество результатов на странице. По умолчанию 25
    
    Returns:
        tuple: Кортеж из двух элементов:
            - list[Airport]: Список объектов Airport для текущей страницы
            - int: Общее количество найденных аэропортов
    
    Example:
        >>> airports, total = get_airports_in_coords(db, 50.0, 60.0, 30.0, 40.0)
        >>> print(f"Найдено {total} аэропортов")
    """
    offset = (page - 1) * per_page
    query = db.query(Airport).filter(
        Airport.latitude.between(lat_min, lat_max),
        Airport.longitude.between(lon_min, lon_max)
    )
    total = query.count()
    items = query.offset(offset).limit(per_page).all()
    return items, total


def get_airport_by_city_country(db: Session, city: str, country: str, 
                                page: int = 1, per_page: int = 25):
    """
    Поиск аэропортов по названию города и страны.
    
    Выполняет регистронезависимый поиск с использованием частичного совпадения.
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
        city (str): Название города (поддерживается частичное совпадение)
        country (str): Название страны (поддерживается частичное совпадение)
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        per_page (int, optional): Количество результатов на странице. По умолчанию 25
    
    Returns:
        tuple: Кортеж из двух элементов:
            - list[Airport]: Список объектов Airport для текущей страницы
            - int: Общее количество найденных аэропортов
    
    Example:
        >>> airports, total = get_airport_by_city_country(db, "Moscow", "Russia")
        >>> for airport in airports:
        ...     print(airport.name)
    """
    offset = (page - 1) * per_page
    query = db.query(Airport).filter(
        Airport.city.ilike(f"%{city}%"), 
        Airport.country.ilike(f"%{country}%")
    )
    total = query.count()
    items = query.offset(offset).limit(per_page).all()
    return items, total


def get_flights_to_from_city(db: Session, city: str, country: str, 
                             page: int = 1, per_page: int = 25):
    """
    Поиск всех рейсов в город или из города.
    
    Находит все маршруты, где город является либо точкой отправления, 
    либо точкой назначения.
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
        city (str): Название города (поддерживается частичное совпадение)
        country (str): Название страны (поддерживается частичное совпадение)
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        per_page (int, optional): Количество результатов на странице. По умолчанию 25
    
    Returns:
        tuple: Кортеж из двух элементов:
            - list[Route]: Список объектов Route для текущей страницы
            - int: Общее количество найденных маршрутов
    
    Note:
        Если в указанном городе не найдено ни одного аэропорта, 
        возвращается пустой список и 0.
    
    Example:
        >>> routes, total = get_flights_to_from_city(db, "London", "United Kingdom")
        >>> print(f"Найдено {total} рейсов")
    """
    offset = (page - 1) * per_page
    # Находим все аэропорты в указанном городе
    airports = db.query(Airport.id).filter(
        Airport.city.ilike(f"%{city}%"), 
        Airport.country.ilike(f"%{country}%")
    ).all()
    airport_ids = [a.id for a in airports]
    
    if not airport_ids:
        return [], 0
    
    # Ищем рейсы, где эти аэропорты являются источником или назначением
    query = db.query(Route).filter(
        (Route.source_id.in_(airport_ids)) | (Route.dest_id.in_(airport_ids))
    )
    total = query.count()
    items = query.offset(offset).limit(per_page).all()
    return items, total


def get_direct_flights_between_cities(db: Session, city1: str, country1: str, 
                                     city2: str, country2: str, 
                                     page: int = 1, per_page: int = 25):
    """
    Поиск прямых рейсов между двумя городами.
    
    Находит беспосадочные рейсы (stops == 0) в обоих направлениях 
    между указанными городами.
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
        city1 (str): Название первого города
        country1 (str): Название страны первого города
        city2 (str): Название второго города
        country2 (str): Название страны второго города
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        per_page (int, optional): Количество результатов на странице. По умолчанию 25
    
    Returns:
        tuple: Кортеж из двух элементов:
            - list[Route]: Список объектов Route для текущей страницы
            - int: Общее количество найденных прямых рейсов
    
    Note:
        Функция ищет рейсы в обоих направлениях (город1 -> город2 и город2 -> город1).
        Если в одном из городов не найдено аэропортов, возвращается пустой список.
    
    Example:
        >>> routes, total = get_direct_flights_between_cities(
        ...     db, "Paris", "France", "Berlin", "Germany"
        ... )
        >>> print(f"Найдено {total} прямых рейсов")
    """
    offset = (page - 1) * per_page
    
    # Находим аэропорты в первом городе
    airports1 = db.query(Airport.id).filter(
        Airport.city.ilike(f"%{city1}%"), 
        Airport.country.ilike(f"%{country1}%")
    ).all()
    
    # Находим аэропорты во втором городе
    airports2 = db.query(Airport.id).filter(
        Airport.city.ilike(f"%{city2}%"), 
        Airport.country.ilike(f"%{country2}%")
    ).all()
    
    ids1 = [a.id for a in airports1]
    ids2 = [a.id for a in airports2]
    
    if not ids1 or not ids2:
        return [], 0
    
    # Ищем прямые рейсы (без пересадок) в обоих направлениях
    query = db.query(Route).filter(
        ((Route.source_id.in_(ids1)) & (Route.dest_id.in_(ids2))) |
        ((Route.source_id.in_(ids2)) & (Route.dest_id.in_(ids1)))
    ).filter(Route.stops == 0)
    
    total = query.count()
    items = query.offset(offset).limit(per_page).all()
    return items, total


def get_unique_cities(db: Session):
    """
    Получение списка всех уникальных городов из базы данных.
    
    Используется для автокомплита в формах поиска.
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
    
    Returns:
        list[str]: Список уникальных названий городов
    
    Example:
        >>> cities = get_unique_cities(db)
        >>> print(cities[:5])  # Первые 5 городов
    """
    return [row[0] for row in db.query(Airport.city).distinct().all()]


def get_unique_countries(db: Session):
    """
    Получение списка всех уникальных стран из базы данных.
    
    Используется для автокомплита в формах поиска.
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
    
    Returns:
        list[str]: Список уникальных названий стран
    
    Example:
        >>> countries = get_unique_countries(db)
        >>> print(len(countries))  # Количество стран
    """
    return [row[0] for row in db.query(Airport.country).distinct().all()]


def get_connecting_flights(db: Session, city1: str, country1: str, 
                           city2: str, country2: str, 
                           page: int = 1, per_page: int = 25):
    """
    Поиск рейсов с одной стыковкой между двумя городами.
    
    Находит маршруты вида A -> X -> B, где:
    - A - город отправления (city1)
    - X - промежуточный город (стыковка)
    - B - город назначения (city2)
    
    Оба сегмента должны быть прямыми рейсами (stops == 0).
    
    Args:
        db (Session): Сессия базы данных SQLAlchemy
        city1 (str): Название города отправления
        country1 (str): Название страны города отправления
        city2 (str): Название города назначения
        country2 (str): Название страны города назначения
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        per_page (int, optional): Количество результатов на странице. По умолчанию 25
    
    Returns:
        tuple: Кортеж из двух элементов:
            - list[object]: Список объектов с информацией о рейсах со стыковкой.
              Каждый объект содержит поля:
                - airline1: Код авиакомпании первого сегмента
                - from1: Код аэропорта отправления
                - from_city: Название города отправления
                - via: Код аэропорта стыковки
                - via_city: Название города стыковки
                - airline2: Код авиакомпании второго сегмента
                - to: Код аэропорта назначения
                - to_city: Название города назначения
            - int: Общее количество найденных маршрутов со стыковкой
    
    Algorithm:
        1. Находим все аэропорты в городах отправления и назначения
        2. Находим все прямые рейсы из города отправления
        3. Определяем возможные города стыковки
        4. Находим прямые рейсы из городов стыковки в город назначения
        5. Формируем полные маршруты, где конечный аэропорт первого сегмента
           совпадает с начальным аэропортом второго сегмента
    
    Note:
        - Если в одном из городов не найдено аэропортов, возвращается пустой список
        - Результаты формируются в памяти и затем пагинируются
        - Может быть ресурсоемкой операцией для популярных направлений
    
    Example:
        >>> flights, total = get_connecting_flights(
        ...     db, "Moscow", "Russia", "Tokyo", "Japan"
        ... )
        >>> for flight in flights[:3]:
        ...     print(f"{flight.from1} -> {flight.via} -> {flight.to}")
    """
    offset = (page - 1) * per_page

    # Аэропорты отправления
    dep_airports = db.query(Airport).filter(
        Airport.city.ilike(f"%{city1}%"),
        Airport.country.ilike(f"%{country1}%")
    ).all()
    dep_ids = [a.id for a in dep_airports]

    # Аэропорты прибытия
    arr_airports = db.query(Airport).filter(
        Airport.city.ilike(f"%{city2}%"),
        Airport.country.ilike(f"%{country2}%")
    ).all()
    arr_ids = [a.id for a in arr_airports]

    if not dep_ids or not arr_ids:
        return [], 0

    # Первый сегмент: рейсы из города отправления
    first_legs = db.query(Route).filter(
        Route.source_id.in_(dep_ids),
        Route.stops == 0
    ).all()

    if not first_legs:
        return [], 0

    # Собираем возможные стыковочные аэропорты (уникальные)
    via_ids = list(set(leg.dest_id for leg in first_legs))

    # Второй сегмент: рейсы из стыковочных аэропортов в город назначения
    second_legs = db.query(Route).filter(
        Route.source_id.in_(via_ids),
        Route.dest_id.in_(arr_ids),
        Route.stops == 0
    ).all()

    # Формируем полные маршруты
    results = []
    for first in first_legs:
        for second in second_legs:
            # Проверяем, что конечный аэропорт первого сегмента
            # совпадает с начальным аэропортом второго сегмента
            if first.dest_id == second.source_id:
                # Получаем информацию об аэропортах
                from_airport = db.query(Airport).filter(
                    Airport.id == first.source_id
                ).first()
                via_airport = db.query(Airport).filter(
                    Airport.id == first.dest_id
                ).first()
                to_airport = db.query(Airport).filter(
                    Airport.id == second.dest_id
                ).first()

                # Создаем объект с информацией о маршруте
                results.append(type('obj', (), {
                    'airline1': first.airline_code or "Unknown",
                    'from1': from_airport.iata or from_airport.icao or "N/A",
                    'from_city': from_airport.city,
                    'via': via_airport.iata or via_airport.icao or "N/A",
                    'via_city': via_airport.city,
                    'airline2': second.airline_code or "Unknown",
                    'to': to_airport.iata or to_airport.icao or "N/A",
                    'to_city': to_airport.city
                }))

    total = len(results)
    # Применяем пагинацию к результатам в памяти
    paginated = results[offset:offset + per_page]

    return paginated, total