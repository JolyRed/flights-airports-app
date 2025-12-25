"""
Модуль main.py - Основное веб-приложение FastAPI.

Содержит все маршруты (endpoints) для веб-интерфейса:
- Главная страница
- Поиск аэропортов по координатам
- Поиск аэропортов по городу и стране
- Поиск рейсов в/из города
- Поиск прямых рейсов между городами
- Поиск рейсов с одной стыковкой
- API endpoints для автокомплита

Приложение использует Jinja2 шаблоны для рендеринга HTML.
"""

from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from database import SessionLocal
from crud import *
from sqlalchemy.orm import Session

# Создание экземпляра приложения FastAPI
app = FastAPI()

# Подключение статических файлов (CSS, JS, изображения)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонизатора Jinja2
templates = Jinja2Templates(directory="templates")


def get_db():
    """
    Dependency функция для получения сессии базы данных.
    
    Создает новую сессию для каждого запроса и автоматически закрывает её
    после завершения обработки запроса.
    
    Yields:
        Session: Сессия SQLAlchemy для работы с базой данных
    
    Note:
        Используется как зависимость FastAPI через Depends(get_db)
    
    Example:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            # db будет автоматически создана и закрыта
            return db.query(Airport).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Главная страница приложения.
    
    Отображает страницу с меню навигации и описанием функционала.
    
    Args:
        request (Request): Объект запроса FastAPI
    
    Returns:
        TemplateResponse: Отрендеренный HTML шаблон index.html
    
    Route:
        GET /
    """
    return templates.TemplateResponse("index.html", {"request": request})


# ==================== Координаты ====================

@app.get("/coord_search")
def coord_search(
    request: Request,
    lat_min: float = None, 
    lat_max: float = None,
    lon_min: float = None, 
    lon_max: float = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Поиск аэропортов в заданном диапазоне координат (GET).
    
    Если все параметры координат предоставлены, выполняет поиск и отображает результаты.
    Если параметры отсутствуют, отображает форму для ввода координат.
    
    Args:
        request (Request): Объект запроса FastAPI
        lat_min (float, optional): Минимальная широта
        lat_max (float, optional): Максимальная широта
        lon_min (float, optional): Минимальная долгота
        lon_max (float, optional): Максимальная долгота
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        TemplateResponse: 
            - results_table.html с результатами поиска (если параметры заданы)
            - coord_search.html с формой поиска (если параметры не заданы)
    
    Route:
        GET /coord_search?lat_min=50&lat_max=60&lon_min=30&lon_max=40&page=1
    
    Example:
        URL: /coord_search?lat_min=55&lat_max=56&lon_min=37&lon_max=38
        Найдет все аэропорты в районе Москвы
    """
    # Проверяем, что все параметры координат предоставлены
    if all(v is not None for v in [lat_min, lat_max, lon_min, lon_max]):
        # Выполняем поиск
        items, total = get_airports_in_coords(db, lat_min, lat_max, lon_min, lon_max, page)
        pages = (total + 24) // 25
        
        return templates.TemplateResponse("results_table.html", {
            "request": request,
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "title": "Аэропорты в диапазоне координат",
            "type": "airport"
        })
    
    # Если параметров нет, показываем форму
    return templates.TemplateResponse("coord_search.html", {"request": request})


@app.post("/coord_search")
def coord_post(
    lat_min: float = Form(...), 
    lat_max: float = Form(...),
    lon_min: float = Form(...), 
    lon_max: float = Form(...)
):
    """
    Обработка формы поиска по координатам (POST).
    
    Принимает данные из формы и перенаправляет на GET endpoint с параметрами.
    
    Args:
        lat_min (float): Минимальная широта из формы
        lat_max (float): Максимальная широта из формы
        lon_min (float): Минимальная долгота из формы
        lon_max (float): Максимальная долгота из формы
    
    Returns:
        RedirectResponse: Перенаправление на GET /coord_search с query параметрами
    
    Route:
        POST /coord_search
    
    Note:
        Использует статус код 303 (See Other) для корректного редиректа после POST
    """
    return RedirectResponse(
        url=f"/coord_search?lat_min={lat_min}&lat_max={lat_max}&lon_min={lon_min}&lon_max={lon_max}&page=1",
        status_code=303
    )


# ==================== По городу и стране (аэропорты) ====================

@app.get("/city_search")
def city_search(
    request: Request, 
    city: str = None, 
    country: str = None, 
    page: int = 1, 
    db: Session = Depends(get_db)
):
    """
    Поиск аэропортов по названию города и страны (GET).
    
    Если параметры поиска предоставлены, выполняет поиск и отображает результаты.
    Если параметры отсутствуют, отображает форму для ввода данных.
    
    Args:
        request (Request): Объект запроса FastAPI
        city (str, optional): Название города для поиска
        country (str, optional): Название страны для поиска
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        TemplateResponse:
            - results_table.html с найденными аэропортами (если параметры заданы)
            - city_search.html с формой поиска (если параметры не заданы)
    
    Route:
        GET /city_search?city=Moscow&country=Russia&page=1
    
    Example:
        URL: /city_search?city=London&country=United Kingdom
        Найдет все аэропорты в Лондоне
    """
    if city and country:
        items, total = get_airport_by_city_country(db, city, country, page)
        pages = (total + 24) // 25
        
        return templates.TemplateResponse("results_table.html", {
            "request": request,
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "title": f"Аэропорты в {city}, {country}",
            "type": "airport"
        })
    
    return templates.TemplateResponse("city_search.html", {"request": request})


@app.post("/city_search")
def city_post(city: str = Form(...), country: str = Form(...)):
    """
    Обработка формы поиска аэропортов (POST).
    
    Принимает данные из формы и перенаправляет на GET endpoint с параметрами.
    
    Args:
        city (str): Название города из формы
        country (str): Название страны из формы
    
    Returns:
        RedirectResponse: Перенаправление на GET /city_search с query параметрами
    
    Route:
        POST /city_search
    """
    return RedirectResponse(
        url=f"/city_search?city={city}&country={country}&page=1", 
        status_code=303
    )


# ==================== Рейсы в/из города ====================

@app.get("/flights_city")
def flights_city(
    request: Request, 
    city: str = None, 
    country: str = None, 
    page: int = 1, 
    db: Session = Depends(get_db)
):
    """
    Поиск всех рейсов в город или из города (GET).
    
    Находит все маршруты, где указанный город является либо точкой отправления,
    либо точкой назначения.
    
    Args:
        request (Request): Объект запроса FastAPI
        city (str, optional): Название города для поиска
        country (str, optional): Название страны для поиска
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        TemplateResponse:
            - results_table.html со списком рейсов (если параметры заданы)
            - flights_city.html с формой поиска (если параметры не заданы)
    
    Route:
        GET /flights_city?city=Paris&country=France&page=1
    
    Example:
        URL: /flights_city?city=Dubai&country=United Arab Emirates
        Найдет все рейсы в Дубай или из Дубая
    """
    if city and country:
        items, total = get_flights_to_from_city(db, city, country, page)
        pages = (total + 24) // 25
        
        return templates.TemplateResponse("results_table.html", {
            "request": request,
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "title": f"Рейсы в/из {city}, {country}",
            "type": "route"
        })
    
    return templates.TemplateResponse("flights_city.html", {"request": request})


@app.post("/flights_city")
def flights_post(city: str = Form(...), country: str = Form(...)):
    """
    Обработка формы поиска рейсов (POST).
    
    Принимает данные из формы и перенаправляет на GET endpoint с параметрами.
    
    Args:
        city (str): Название города из формы
        country (str): Название страны из формы
    
    Returns:
        RedirectResponse: Перенаправление на GET /flights_city с query параметрами
    
    Route:
        POST /flights_city
    """
    return RedirectResponse(
        url=f"/flights_city?city={city}&country={country}&page=1", 
        status_code=303
    )


# ==================== Прямые рейсы между городами ====================

@app.get("/direct_flights")
def direct_flights(
    request: Request,
    city1: str = None, 
    country1: str = None,
    city2: str = None, 
    country2: str = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Поиск прямых беспосадочных рейсов между двумя городами (GET).
    
    Находит все прямые рейсы (stops == 0) между указанными городами
    в обоих направлениях.
    
    Args:
        request (Request): Объект запроса FastAPI
        city1 (str, optional): Название первого города
        country1 (str, optional): Название страны первого города
        city2 (str, optional): Название второго города
        country2 (str, optional): Название страны второго города
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        TemplateResponse:
            - results_table.html со списком прямых рейсов (если параметры заданы)
            - direct_flights.html с формой поиска (если параметры не заданы)
    
    Route:
        GET /direct_flights?city1=Moscow&country1=Russia&city2=Paris&country2=France&page=1
    
    Example:
        URL: /direct_flights?city1=New York&country1=United States&city2=London&country2=United Kingdom
        Найдет все прямые рейсы между Нью-Йорком и Лондоном
    """
    if all(v is not None for v in [city1, country1, city2, country2]):
        items, total = get_direct_flights_between_cities(db, city1, country1, city2, country2, page)
        pages = (total + 24) // 25
        
        return templates.TemplateResponse("results_table.html", {
            "request": request,
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "title": f"Прямые рейсы между {city1} и {city2}",
            "type": "route"
        })
    
    return templates.TemplateResponse("direct_flights.html", {"request": request})


@app.post("/direct_flights")
def direct_post(
    city1: str = Form(...), 
    country1: str = Form(...),
    city2: str = Form(...), 
    country2: str = Form(...)
):
    """
    Обработка формы поиска прямых рейсов (POST).
    
    Принимает данные из формы и перенаправляет на GET endpoint с параметрами.
    
    Args:
        city1 (str): Название первого города из формы
        country1 (str): Название страны первого города из формы
        city2 (str): Название второго города из формы
        country2 (str): Название страны второго города из формы
    
    Returns:
        RedirectResponse: Перенаправление на GET /direct_flights с query параметрами
    
    Route:
        POST /direct_flights
    """
    return RedirectResponse(
        url=f"/direct_flights?city1={city1}&country1={country1}&city2={city2}&country2={country2}&page=1",
        status_code=303
    )


# ==================== Рейсы со стыковкой ====================

@app.get("/connecting_flights")
def connecting_flights(
    request: Request,
    city1: str = None, 
    country1: str = None,
    city2: str = None, 
    country2: str = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """
    Поиск рейсов с одной стыковкой между двумя городами (GET).
    
    Находит маршруты вида A -> X -> B, где X - промежуточный город.
    Оба сегмента должны быть прямыми рейсами.
    
    Args:
        request (Request): Объект запроса FastAPI
        city1 (str, optional): Название города отправления
        country1 (str, optional): Название страны города отправления
        city2 (str, optional): Название города назначения
        country2 (str, optional): Название страны города назначения
        page (int, optional): Номер страницы для пагинации. По умолчанию 1
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        TemplateResponse:
            - results_table.html со списком рейсов со стыковкой (если параметры заданы)
            - connecting_flights.html с формой поиска (если параметры не заданы)
    
    Route:
        GET /connecting_flights?city1=Moscow&country1=Russia&city2=Tokyo&country2=Japan&page=1
    
    Note:
        Эта операция может быть ресурсоемкой для популярных направлений,
        так как рассматривает все возможные комбинации стыковок.
    
    Example:
        URL: /connecting_flights?city1=Berlin&country1=Germany&city2=Singapore&country2=Singapore
        Найдет все рейсы с одной стыковкой между Берлином и Сингапуром
    """
    if all(v is not None for v in [city1, country1, city2, country2]):
        items, total = get_connecting_flights(db, city1, country1, city2, country2, page)
        pages = (total + 24) // 25
        
        return templates.TemplateResponse("results_table.html", {
            "request": request,
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
            "title": f"Рейсы со стыковкой: {city1} → {city2}",
            "type": "connecting"
        })
    
    # Если параметров нет — показываем форму
    return templates.TemplateResponse("connecting_flights.html", {"request": request})


@app.post("/connecting_flights")
def connecting_post(
    city1: str = Form(...), 
    country1: str = Form(...), 
    city2: str = Form(...), 
    country2: str = Form(...)
):
    """
    Обработка формы поиска рейсов со стыковкой (POST).
    
    Принимает данные из формы и перенаправляет на GET endpoint с параметрами.
    
    Args:
        city1 (str): Название города отправления из формы
        country1 (str): Название страны города отправления из формы
        city2 (str): Название города назначения из формы
        country2 (str): Название страны города назначения из формы
    
    Returns:
        RedirectResponse: Перенаправление на GET /connecting_flights с query параметрами
    
    Route:
        POST /connecting_flights
    """
    return RedirectResponse(
        url=f"/connecting_flights?city1={city1}&country1={country1}&city2={city2}&country2={country2}&page=1",
        status_code=303
    )


# ==================== API для автокомплита ====================

@app.get("/api/cities")
def api_cities(q: str = "", db: Session = Depends(get_db)):
    """
    API endpoint для автокомплита названий городов.
    
    Возвращает список городов, содержащих указанную подстроку.
    Используется для динамических подсказок в формах поиска.
    
    Args:
        q (str, optional): Поисковый запрос (подстрока). По умолчанию пустая строка
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        list[str]: Список названий городов (максимум 10 результатов),
                   соответствующих поисковому запросу
    
    Route:
        GET /api/cities?q=Mos
    
    Response Example:
        ["Moscow", "Mosul", "Mostar"]
    
    Note:
        - Поиск регистронезависимый
        - Возвращает максимум 10 первых совпадений
        - Результаты не сортируются по релевантности
    """
    cities = get_unique_cities(db)
    return [c for c in cities if q.lower() in c.lower()][:10]


@app.get("/api/countries")
def api_countries(q: str = "", db: Session = Depends(get_db)):
    """
    API endpoint для автокомплита названий стран.
    
    Возвращает список стран, содержащих указанную подстроку.
    Используется для динамических подсказок в формах поиска.
    
    Args:
        q (str, optional): Поисковый запрос (подстрока). По умолчанию пустая строка
        db (Session): Сессия базы данных (внедряется автоматически)
    
    Returns:
        list[str]: Список названий стран (максимум 10 результатов),
                   соответствующих поисковому запросу
    
    Route:
        GET /api/countries?q=Uni
    
    Response Example:
        ["United States", "United Kingdom", "United Arab Emirates"]
    
    Note:
        - Поиск регистронезависимый
        - Возвращает максимум 10 первых совпадений
        - Результаты не сортируются по релевантности
    """
    countries = get_unique_countries(db)
    return [c for c in countries if q.lower() in c.lower()][:10]