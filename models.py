"""
Модуль models.py - Модели данных для работы с базой данных.

Содержит ORM-модели SQLAlchemy для представления основных сущностей:
- Airport: Аэропорты с их географическими координатами и кодами
- Airline: Авиакомпании с их идентификационными данными
- Route: Маршруты полетов между аэропортами

Модели связаны через внешние ключи для обеспечения целостности данных.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Airport(Base):
    """
    Модель аэропорта.
    
    Представляет информацию об аэропорте, включая его название, местоположение,
    коды IATA/ICAO и географические координаты.
    
    Attributes:
        id (int): Уникальный идентификатор аэропорта (OpenFlights ID)
        name (str): Полное название аэропорта
        city (str): Город, в котором расположен аэропорт
        country (str): Страна расположения аэропорта
        iata (str): Трёхбуквенный код IATA (например, "SVO" для Шереметьево)
        icao (str): Четырёхбуквенный код ICAO (например, "UUEE" для Шереметьево)
        latitude (float): Широта местоположения аэропорта в десятичных градусах
        longitude (float): Долгота местоположения аэропорта в десятичных градусах
        altitude (int): Высота над уровнем моря в футах
        timezone (float): Часовой пояс относительно UTC
        dst (str): Правило перехода на летнее время
        tz (str): Название часового пояса (например, "Europe/Moscow")
    
    Relationships:
        departures (list[Route]): Список рейсов, вылетающих из этого аэропорта
        arrivals (list[Route]): Список рейсов, прилетающих в этот аэропорт
    
    Example:
        >>> airport = Airport(
        ...     name="Sheremetyevo International Airport",
        ...     city="Moscow",
        ...     country="Russia",
        ...     iata="SVO",
        ...     latitude=55.9726,
        ...     longitude=37.4146
        ... )
    """
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    city = Column(String)
    country = Column(String)
    iata = Column(String)
    icao = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Integer)
    timezone = Column(Float)
    dst = Column(String)
    tz = Column(String)

    # Связи для удобства навигации между таблицами
    departures = relationship("Route", foreign_keys="Route.source_id", back_populates="source")
    arrivals = relationship("Route", foreign_keys="Route.dest_id", back_populates="dest")


class Airline(Base):
    """
    Модель авиакомпании.
    
    Представляет информацию об авиакомпании, включая её название, коды и статус.
    
    Attributes:
        id (int): Уникальный идентификатор авиакомпании
        name (str): Полное название авиакомпании
        alias (str): Альтернативное название или псевдоним
        iata (str): Двухбуквенный код IATA (например, "SU" для Аэрофлот)
        icao (str): Трёхбуквенный код ICAO (например, "AFL" для Аэрофлот)
        callsign (str): Позывной авиакомпании для радиосвязи
        country (str): Страна регистрации авиакомпании
        active (str): Статус активности авиакомпании ("Y" - активна, "N" - не активна)
    
    Relationships:
        routes (list[Route]): Список маршрутов, обслуживаемых этой авиакомпанией
    
    Example:
        >>> airline = Airline(
        ...     name="Aeroflot",
        ...     iata="SU",
        ...     icao="AFL",
        ...     country="Russia",
        ...     active="Y"
        ... )
    """
    __tablename__ = "airlines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    alias = Column(String)
    iata = Column(String)
    icao = Column(String)
    callsign = Column(String)
    country = Column(String)
    active = Column(String)

    routes = relationship("Route", back_populates="airline")


class Route(Base):
    """
    Модель маршрута полёта.
    
    Представляет информацию о маршруте между двумя аэропортами, включая
    авиакомпанию, выполняющую рейс, количество стыковок и используемое оборудование.
    
    Attributes:
        id (int): Уникальный идентификатор маршрута (автоинкремент)
        airline_code (str): Код авиакомпании (IATA или ICAO)
        airline_id (int): Внешний ключ на таблицу airlines
        source_code (str): Код аэропорта отправления (IATA или ICAO)
        source_id (int): Внешний ключ на таблицу airports (аэропорт отправления)
        dest_code (str): Код аэропорта назначения (IATA или ICAO)
        dest_id (int): Внешний ключ на таблицу airports (аэропорт назначения)
        codeshare (str): Признак кодшеринга (совместного рейса)
        stops (int): Количество промежуточных остановок (0 = прямой рейс)
        equipment (str): Типы используемых воздушных судов (через пробел)
    
    Relationships:
        airline (Airline): Авиакомпания, выполняющая рейс
        source (Airport): Аэропорт отправления
        dest (Airport): Аэропорт назначения
    
    Note:
        - stops = 0 означает прямой беспосадочный рейс
        - stops > 0 означает рейс с техническими посадками
        - equipment может содержать несколько типов ВС, например "737 320"
    
    Example:
        >>> route = Route(
        ...     airline_code="SU",
        ...     source_code="SVO",
        ...     dest_code="LED",
        ...     stops=0,
        ...     equipment="320"
        ... )
    """
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    airline_code = Column(String)
    airline_id = Column(Integer, ForeignKey("airlines.id"))
    source_code = Column(String)
    source_id = Column(Integer, ForeignKey("airports.id"))
    dest_code = Column(String)
    dest_id = Column(Integer, ForeignKey("airports.id"))
    codeshare = Column(String)
    stops = Column(Integer)
    equipment = Column(String)

    # Связи для навигации между таблицами
    airline = relationship("Airline", back_populates="routes")
    source = relationship("Airport", foreign_keys=[source_id], back_populates="departures")
    dest = relationship("Airport", foreign_keys=[dest_id], back_populates="arrivals")