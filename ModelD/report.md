# Система анализа рисков туристических маршрутов

## Общее описание

Система автоматического анализа туристических маршрутов, которая:
- Собирает GPX-треки с OpenStreetMap
- Обогащает их данными о погоде, рельефе, POI
- Классифицирует риски с помощью ML
- Визуализирует опасные участки на карте
- Предоставляет API для прогнозов

## Установка и запуск

### Требования
- Python 3.9+
- MySQL 8.0+

### 1. Установка зависимостей

### Введите команду для создания виртуального окружения:

python -m venv .venv

### Введите команду для установки библиотек:

pip install -r requirements.txt

### В базе данных создайте 2 таблицы:

CREATE TABLE track (
    track_id INT AUTO_INCREMENT PRIMARY KEY,
    region VARCHAR(255),
    temperature FLOAT,
    weather VARCHAR(100),
    terrain_type VARCHAR(50),
    step_frequency FLOAT,
    datetime DATETIME,
    season VARCHAR(20),
    gpx_data TEXT
);

CREATE TABLE points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    track_id INT,
    latitude FLOAT,
    longitude FLOAT,
    elevation FLOAT,
    temperature FLOAT,
    weather VARCHAR(100),
    terrain_type VARCHAR(50),
    poi_objects TEXT,
    step_frequency FLOAT,
    region VARCHAR(255),
    datetime DATETIME,
    season VARCHAR(20),
    year INT,
    month INT,
    day INT,
    week_day INT,
    time_of_day VARCHAR(20),
    FOREIGN KEY (track_id) REFERENCES track(track_id)
);

### Порядок запуска модулей:

python modela.py        # Сбор данных (модуль А)
python modelv.py        # Обучение ML моделей (модуль В)
python try_g.py         # Запуск API (модуль Г) - порт 8054
python Api_Dash.py      # Веб-интерфейс (модуль Г) - порт 8059
python modelb.py        # Аналитический дашборд (модуль Б) - порт 8053

## Модуль А: Сбор данных
**Файл:** modela.py

**Функциональность:**
- Загрузка GPX-треков с OpenStreetMap
- Парсинг: координаты, высота, время
- Обогащение: погода (Open-Meteo), регион (Nominatim), POI (Overpass)
- Сохранение: MySQL база + CSV файл
- Генерация карт маршрутов

**Пример:**
python
model = Modela()
links = ['https://www.openstreetmap.org/trace/12174780/data.gpx']
for link in links:
    gpx_file = model.download_gpx(link)
    data, point_data = model.parse_gpx(gpx_file)
    model.save_data(data, point_data)

## Модуль Б: Аналитика
**Файл:** modelb.py

**Возможности:**

- Фильтры: регион, время суток

- Графики: шаги/сезон, температура/время, высота/шаги

- Кластеризация: K-means, DBSCAN

- Метрики: silhouette, calinski-harabasz

**Карта рисков**

**Доступ:** http://localhost:8053

## Модуль В: ML модели
**Файл:** modelv.py

**Алгоритмы:**

- Random Forest

- Logistic Regression

- K-Nearest Neighbors

**Метрики:**

- Accuracy: 0.82-0.89

- Precision: 0.81-0.88

- F1-score: 0.80-0.87

**Функционал:**

- Классификация рисков (Низкий/Средний/Высокий)

- Классификация эвакуации

- Непрерывное обучение при дрифте данных

- Версионирование моделей

## Модуль Г: API и интерфейс
**FastAPI** (try_g.py)
**Порт:** 8054
Эндпоинт: POST /risk

**Пример запроса для апи:**

latitude: 51.5 - Ширина
longitude: 52.3 - Долгота
elevation: 1453 - Высота
terrain_type: Горы - Тип местности
track_date: 2026-04-02 - Дата

**Пример ответа в формате json:**

`coordinates`:{
    'latitude': 51.5,
    'longitude': 52.3,
},
`prediction`: {
    'risk': Высокий,
    'evacuation': Средний,
},
`factors`: {
    'temperature': -5,
    'elevation': 1453,
    'terrain': Горы,
    'weather': Snow fall,
}

## Веб-интерфейс (Api_Dash.py)
**Порт:** 8059
**Функции:** выбор региона, даты, карта с цветными рисками, линия трека

**Установка**
bash
pip install -r requirements.txt
**MySQL:**

sql
CREATE DATABASE track_db2;
-- таблицы track и points
Запуск:

bash
python modela.py        # Сбор данных
python modelv.py        # Обучение ML
python try_g.py         # API (8054)
python Api_Dash.py      # Веб (8059)
python modelb.py        # Аналитика (8053)

**Форматы данных:**

CSV: track_dataset.csv 

Модель: model.pkl

Версии: version.json

Логи: log.csv