import pandas as pd
import sqlite3
import gpxpy
from geopy.geocoders import Nominatim
import requests
from datetime import datetime
import os
import contextily as ctx
from PIL import Image, ImageEnhance
import matplotlib.pyplot as plt
import numpy as np

class ModelA:
    def __init__(self):
        self.create_db()
    
    # Создание бд
    def create_db(self):
        conn = sqlite3.connect('track_db.db')
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS tracks (
                    track_id INTEGER AUTO_INCREMENT PRIMARY KEY,
                    region TEXT NOT NULL,
                    weather TEXT NOT NULL,
                    terrain_type TEXT NOT NULL,
                    temperature FLOAT NOT NULL,
                    datetime DATETIME NOT NULL,
                    season TEXT NOT NULL,
                    gpx LONGTEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS points (
                    point_id INTEGER AUTO_INCREMENT PRIMARY KEY,
                    track_id INTEGER NOT NULL,
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL,
                    elevation FLOAT NOT NULL,
                    region TEXT NOT NULL,
                    step_frequncy FLOAT NOT NULL,
                    temperature FLOAT NOT NULL,
                    weather TEXT NOT NULL,
                    terrain_type TEXT NOT NULL,
                    poi_objects TEXT NOT NULL,
                    datetime DATETIME NOT NULL,
                    season TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    time_of_day TEXT NOT NULL,
                    FOREIGN KEY (track_id) REFERENCES tracks(track_id))''')
        conn.commit()
        conn.close()
        print('База данных создана')
    
    # Получение файла по ссылке
    def download_gpx(self, link):
        response = requests.get(link, timeout=50)
        if response.status_code == 200:
            gpx_data = response.content
            return gpx_data
    
    # Расчет частоты шагов
    def get_step(self, points, timestamps):
        sorted_time = sorted(timestamps)
        difference = sorted_time[-1] - sorted_time[0]
        total_seconds = difference.total_seconds()  
        step_frequncy = len(points) / total_seconds
        print(f'Частота шагов пощитана {step_frequncy * 60}')
        return step_frequncy * 60
    
    # Получение рениона через библиотеку
    def get_region(self, latitude, longitude):
        geolocator = Nominatim(user_agent="my_app")
        location = geolocator.reverse((latitude, longitude))
        print(f'Регион получен {location.raw["address"]["state"]}')
        return location.raw["address"]["state"]
    
    # Получение обьектов в радиусе 500м 
    def get_poi(self, latitude, longitude, radius=500):
        while True:
            data = f'''[out:json][timeout:50];
            (
                node['natural'](around:{radius},{latitude},{longitude});
                node['building'](around:{radius},{latitude},{longitude});
                node['highway'](around:{radius},{latitude},{longitude});
                node['amenity'](around:{radius},{latitude},{longitude});
                way['natural'](around:{radius},{latitude},{longitude});
                way['building'](around:{radius},{latitude},{longitude});
                way['highway'](around:{radius},{latitude},{longitude});
                way['amenity'](around:{radius},{latitude},{longitude});
            );
            out body;'''
            url = 'https://overpass-api.de/api/interpreter'
            response = requests.post(url=url, data={'data': data})
            print(response.status_code)
            if response.status_code == 200:
                data = response.json()
                objects = []
                elements = data.get('elements', [])
                for element in elements:
                    tags = element.get('tags')
                    if 'building' in tags:
                        objects.append('Здание')              
                    elif 'highway' in tags:
                        objects.append('Дорога')  
                    elif 'natural' in tags:
                        natural_type = tags['natural']
                        if natural_type == 'tree':
                            objects.append('Дерево')
                        elif natural_type == 'wood':
                            objects.append('Лес')
                        elif natural_type == 'water':
                            objects.append('Водоем')
                            
                    elif 'amenity' in tags:
                        amenity_type = tags['amenity']
                        if amenity_type == 'hospital':
                            objects.append('Больница')
                return list(set(objects))
    
    # Расшифровка кодов погоды
    def get_weather_description(self, code):
        if code == 0:
            return "Clear sky"
        elif code in (1, 2, 3):
            return "Mainly clear/partly cloudy/overcast"
        elif code in (45, 48):
            return "Fog"
        elif code in (51, 53, 55):
            return "Drizzle"
        elif code in (56, 57):
            return "Freezing Drizzle"
        elif code in (61, 63, 65):
            return "Rain"
        elif code in (66, 67):
            return "Freezing Rain"
        elif code in (71, 73, 75):
            return "Snow fall"
        elif code == 77:
            return "Snow grains"
        elif code in (80, 81, 82):
            return "Rain showers"
        elif code in (85, 86):
            return "Snow showers"
        elif code == 95:
            return "Thunderstorm"
        elif code in (96, 99):
            return "Thunderstorm with hail"
        else:
            return "Unknown weather"

    # Получение погоды и температуры
    def get_weather(self, latitude, longitude, datetime):
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'hourly': 'temperature_2m,weather_code',
            'timezone': 'auto',
            'start_date': datetime.strftime('%Y-%m-%d'),
            'end_date': datetime.strftime('%Y-%m-%d')
        }
        url = 'https://archive-api.open-meteo.com/v1/archive'
        response = requests.get(url=url, params=params, timeout=100)
        if response.status_code == 200:
            data = response.json()
            temperature = data.get('hourly').get('temperature_2m')[0]
            weather_code = data.get('hourly').get('weather_code')[0]
            weather = self.get_weather_description(weather_code)
            print(f'Погода получена {temperature}, {weather}')
            return temperature, weather
    
    # Получение времяни суток
    def get_time_of_day(self, datetime):
        hour = datetime.hour
        if hour >= 0 and hour <= 6:
            return 'Ночь'
        elif hour >= 7 and hour <= 12:
            return 'Утро'
        elif hour >= 13 and hour <= 18:
            return 'День'
        else:
            return 'Вечер'
        
    # Создание и аугментация изображений
    def create_map(self, points, region):
        if not os.path.exists('ModelA/pictures'):
            os.makedirs('ModelA/pictures')
        fig_name = f'ModelA/pictures/map_{region}'
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        fig, ax = plt.subplots(figsize=(10,10))
        ax.plot(lons, lats, color='red', linewidth=3)
        xmin, xmax, ymin, ymax = min(lons), max(lons), min(lats), max(lats)
        xpad = (xmax - xmin) * 0.1
        ypad = (ymax - ymin) * 0.1
        ax.set_xlim(xmin - xpad, xmax + xpad)
        ax.set_ylim(ymin - ypad, ymax + ypad)
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs='EPSG:4326')
        ax.set_axis_off()
        plt.savefig(f'{fig_name}.jpg', dpi=150)
        plt.close()
        img = Image.open(f'{fig_name}.jpg')
        img.rotate(30).save(f'{fig_name}_rotated.jpg')
        arr = np.array(img)
        shift = np.roll(arr, 30)
        shift[:, :30] = 255
        Image.fromarray(shift).save(f'{fig_name}_shifted.jpg')
        ImageEnhance.Brightness(img).enhance(1.2).save(f'{fig_name}_enchanced.jpg')

    # Парсинг и сбор данных
    def parse_gpx(self, gpx_data):
        gpx = gpxpy.parse(gpx_data)
        points = []
        timestamps = []
        elevations = []

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append(point)
                    timestamps.append(point.time)
                    elevations.append(point.elevation)

        step_frequncy = self.get_step(points, timestamps)

        terrain_type = ''
        elevation_diff = elevations[-1] - elevations[0]
        if elevation_diff > 800:
            terrain_type = 'Горы'
        elif elevation_diff > 500:
            terrain_type = 'Холмы'
        elif elevation_diff > 250:
            terrain_type = 'Пересеченная'
        else:
            terrain_type = 'Равнина'

        region = self.get_region(points[0].latitude, points[0].longitude)

        all_result = []
        poi_cashe = {}
        for i in range(0, len(points), 150):
            group_points = points[i:i + 150]
            poi_cashe[i] = self.get_poi(group_points[0].latitude, group_points[0].longitude)
        
        seasons = ['winter', 'spring', 'summer', 'autumn']
        map_season = {
            'winter': 1,
            'spring': 4,
            'summer': 7,
            'autumn': 10
        }   
        year = 2025

        self.create_map(points, region)

        for season in seasons:
            new_datetime = datetime(int(year), map_season[season], 1, timestamps[0].hour, timestamps[0].minute)
            temperature, weather = self.get_weather(points[0].latitude, points[0].longitude, new_datetime)
            point_data = []
            for i in range(0, len(points), 150):
                group_points = points[i:i + 150]
                objects = poi_cashe.get(i, [])
                for point in group_points:
                    time_diff = point.time - timestamps[0]
                    point_time = new_datetime + time_diff
                    point_data.append({
                            'latitude': point.latitude,
                            'longitude': point.longitude,
                            'elevation': point.elevation,
                            'region': region,
                            'step_frequncy': step_frequncy,
                            'temperature': temperature,
                            'weather': weather,
                            'terrain_type': terrain_type,
                            'poi_objects': objects,
                            'datetime': point_time,
                            'season': season,
                            'year': point_time.year,
                            'month': point_time.month,
                            'day': point_time.day,
                            'time_of_day': self.get_time_of_day(point_time)
                    })
            data = {
                    'region': region,
                    'temperature': temperature,
                    'weather': weather,
                    'terrain_type': terrain_type,
                    'datetime': new_datetime,
                    'season': season,
                    'gpx': gpx
            }

            all_result.append((data, point_data))
        return all_result
    
    # Проверка на дупликат
    def check_track(self, region, datetime):
        conn = sqlite3.connect('track_db.db')
        cur = conn.cursor()
        cur.execute('SELECT track_id FROM tracks WHERE region = ? AND datetime = ?', (region, datetime))
        track_id = cur.fetchone()
        conn.close()
        return track_id
    
    # Сохранение данных
    def save_data(self, data, point_data):
        if not self.check_track(data['region'], data['datetime']) == None:
            print('Трек уже сохранен')
            return None
        
        conn = sqlite3.connect('track_db.db')
        cur = conn.cursor()
        cur.execute('''INSERT INTO tracks (region, temperature, weather, terrain_type, datetime, season, gpx)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', (data['region'],data['temperature'],data['weather'],
                    data['terrain_type'],data['datetime'],data['season'],str(data['gpx'])))
        track_id = cur.lastrowid

        for point in point_data:
            cur.execute('''INSERT INTO points (track_id, latitude, longitude, elevation, region, step_frequncy, temperature,
                        weather, terrain_type, poi_objects, datetime, season, year, month, day, time_of_day) VALUES 
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (track_id,point['latitude'],
                        point['longitude'],point['elevation'],point['region'],point['step_frequncy'],point['temperature'],point['weather'],
                        point['terrain_type'],str(point['poi_objects']),point['datetime'],point['season'],point['year'],point['month'],
                        point['day'],point['time_of_day']))
        conn.commit()
        conn.close()

if __name__ == '__main__':
    model = ModelA()
    links = [
        'https://nasledniki.narod.ru/03_GPS/GPS_Sources/01_Olhinskoe_plateau/Orlenok_Potajnye_Kamni.gpx',
        'https://nasledniki.narod.ru/03_GPS/GPS_Sources/01_Olhinskoe_plateau/R258_Barynya.gpx',
        'https://nasledniki.narod.ru/03_GPS/GPS_Sources/02_Hamar-Daban/Babha_1_peak_Porozhistyy_Solzan.gpx',
        'https://nasledniki.narod.ru/03_GPS/GPS_Sources/03_East_Sayan_Mountains/Mondy_peak_Huruma.gpx'
    ]
    for link in links:
        gpx_data = model.download_gpx(link)
        all_data = model.parse_gpx(gpx_data)
        for data, point_data in all_data:
            model.save_data(data, point_data)