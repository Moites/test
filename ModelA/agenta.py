import pandas as pd
import pymysql
import requests
import gpxpy
import os
import numpy as np
from PIL import Image, ImageEnhance
import contextily as ctx
import matplotlib.pyplot as plt

class Modela:
    def __init__(self):
        self.dataset = 'Files/track_dataset.csv'
        self.create_dataset()
        self.create_db()

    def create_db(self):
        conn = pymysql.connect(user='root', password='', port=3306, host='MySQL-8.0')
        cur = conn.cursor()
        cur.execute('CREATE DATABASE IF NOT EXISTS track_db')
        cur.execute('USE track_db')
        cur.execute('''CREATE TABLE IF NOT EXISTS tracks (
                    track_id INTEGER AUTO_ENCRIMENT PRIMERY KEY,
                    region TEXT NOT NULL,
                    elevation FLOUT NOT NULL,
                    temperature FLOUT NOT NULL,
                    weather TEXT NOT NULL,
                    terrain_type TEXT NOT NULL,
                    step_frequency FLOUT NOT NULL,
                    datetime DATETIME NOT NULL,
                    season TEXT NOT NULL,
                    gpx_data LONGTEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS points (
                    point_id INTEGER AUTO_ENCRIMENT PRIMERY KEY,
                    track_id INTEGER NOT NULL,
                    latitude FLOUT NOT NULL,
                    longitude FLOUT NOT NULL,
                    elevation FLOUT NOT NULL,
                    region TEXT NOT NULL,
                    temperature FLOUT NOT NULL,
                    weather TEXT NOT NULL,
                    terrain_type TEXT NOT NULL,
                    step_frequency FLOUT NOT NULL,
                    poi_objects TEXT NOT NULL,
                    datetime DATETIME NOT NULL,
                    season TEXT NOT NULL,
                    year INTEGET NOT NULL,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    week_day INTEGER NOT NULL,
                    time_of_day TEXT NOT NULL,
                    FOREIGHT KEY (track_id) REFERENCES tracks(track_id))''')

    def create_dataset(self):
        os.makedirs('Files', exist_ok=True)
        if not os.path.exists(self.dataset):
            df = pd.DataFrame(columns=['track_id', 'latitude', 'longitude', 'elevation', 'temperature', 'weather',
                                    'terrain_type', 'poi_objects', 'step_frequency', 'region', 'datetime',
                                    'season', 'year', 'month', 'day', 'week_day', 'time_of_day'])
            df.to_csv(self.dataset, encoding='utf-8', index=False)

    def download_gpx(self, link):
        response = requests.get(link, timeout=50)
        if response.status_code == 200:
            data = response.content
            return data

    def get_step(self, points, timestamps):
        sort_time = sorted(timestamps)
        total_seconds = (sort_time[-1] - sort_time[0]).total_seconds()
        step_frequency = len(points) / total_seconds
        return step_frequency * 60

    def get_weather_description(self, weather_code):
        if weather_code == 0:
            return "Clear sky"
        elif weather_code in (1, 2, 3):
            return "Mainly clear/partly cloudy/overcast"
        elif weather_code in (45, 48):
            return "Fog"
        elif weather_code in (51, 53, 55):
            return "Drizzle"
        elif weather_code in (56, 57):
            return "Freezing Drizzle"
        elif weather_code in (61, 63, 65):
            return "Rain"
        elif weather_code in (66, 67):
            return "Freezing Rain"
        elif weather_code in (71, 73, 75):
            return "Snow fall"
        elif weather_code == 77:
            return "Snow grains"
        elif weather_code in (80, 81, 82):
            return "Rain showers"
        elif weather_code in (85, 86):
            return "Snow showers"
        elif weather_code == 95:
            return "Thunderstorm"
        elif weather_code in (96, 99):
            return "Thunderstorm with hail"
        else:
            return "Unknown weather"

    def get_weather(self, latitude, longitude, date):
        try:
            url = 'https://archive-api.open-meteo.com/v1/archive'
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'start_date': '2026-01-15',
                'end_date': '2026-01-15',
                'daily': 'temperature_2m_max,weathercode',
                'timezone': 'auto'
            }
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                weather_code = data.get('daily').get('weathercode')[0]
                weather = self.get_weather_description(weather_code)
                return data.get('daily').get('temperature_2m_max')[0], weather
        except Exception as e:
            print(f'Ошибка получения метеоданных {e}')

    def get_region(self, latitude, longtitude):
        params = {
            'lat': latitude,
            'lon': longtitude,
            'zoom': 8,
            'accept-language': 'ru',
            'format': 'json'
        }
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'}
        url = 'https://nominatim.openstreetmap.org/reverse'
        response = requests.get(url=url, headers=headers, params=params, timeout=50)
        if response.status_code == 200:
            data = response.json()
            region = data.get('name')
            return region

    def get_poi(self, latitude, longtitude, radius=500):
        data = {f'''[out:json][timeout:50];
                (
                node['building'](around:{radius},{latitude},{longtitude});
                node['highway'](around:{radius},{latitude},{longtitude});
                node['natural'='tree'](around:{radius},{latitude},{longtitude});
                node['natural'='wood'](around:{radius},{latitude},{longtitude});
                node['natural'='water'](around:{radius},{latitude},{longtitude});
                node['amenity'='hospital'](around:{radius},{latitude},{longtitude});
                );
                out body;'''}
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = 'https://overpass-api.de/api/interpreter'
        response = requests.post(url=url, headers=headers, data={'data': data})
        print(response.status_code)
        if response.status_code == 200:
            tags = []
            data = response.json()
            for element in data.get('elements'):
                tag = element.get('tags')
                if tag.get('natural') == 'tree':
                    tags.append('Дерево')
                elif tag.get('natural') == 'wood':
                    tags.append('Дерево')
                elif tag.get('natural') == 'water':
                    tags.append('Вода')
                elif tag.get('amenity') == 'hospital':
                    tags.append('Больница')
                elif 'building' in tag:
                    tags.append('Здание')
                elif 'highway' in tag:
                    tags.append('Дорога')
            return list(set(tags))

    def get_season(self, datetime):
        map = {
            1: 'Зима',
            2: 'Зима',
            3: 'Весна',
            4: 'Весна',
            5: 'Весна',
            6: 'Лето',
            7: 'Лето',
            8: 'Лето',
            9: 'Осень',
            10: 'Осень',
            11: 'Осень',
            12: 'Зима'
        }
        return map.get(datetime.month)

    def get_time_of_day(self, hour):
        if 0 <= hour < 6:
            return 'Ночь'
        elif 6 <= hour < 12:
            return 'Утро'
        elif 12 <= hour < 18:
            return 'День'
        else:
            return 'Вечер'
    
    def create_map(self, points, track_id):
        if not os.path.exists('ModelA/pictures'):
            os.makedirs('ModelA/pictures')
        file_name = f'ModelA/pictures/map{track_id}'
        lons = [p['longitude'] for p in points]
        lats = [p['latitude'] for p in points]
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.plot(lons, lats, color='red', linewidth=3, alpha=0.8)
        xmin, xmax = min(lons), max(lons)
        ymin, ymax = min(lats), max(lats)
        xpad = (xmax - xmin) * 0.1
        ypad = (ymax - ymin) * 0.1
        ax.set_xlim(xmin - xpad, xmax + xpad)
        ax.set_ylim(ymin - ypad, ymax + ypad)
        ctx.add_basemap(ax, crs='EPSG:4326', 
                    source=ctx.providers.OpenStreetMap.Mapnik)
        ax.set_axis_off()
        plt.savefig(f'{file_name}.jpg', dpi=150, bbox_inches='tight', 
                    facecolor='white', pad_inches=0.1)
        plt.close()
        img = Image.open(f'{file_name}.jpg')
        img.rotate(10, fillcolor='white').save(f"{file_name}_rotated.jpg")
        arr = np.array(img)
        shifted = np.roll(arr, 30, axis=1)
        shifted[:, :30] = 255
        Image.fromarray(shifted).save(f"{file_name}_shifted.jpg")
        ImageEnhance.Brightness(img).enhance(1.2).save(f"{file_name}_bright.jpg")

    def parse_gpx(self, gpx_file):
        gpx = gpxpy.parse(gpx_file)
        points = []
        timestamps = []
        elevations = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append(point)
                    timestamps.append(point.time)
                    elevations.append(point.elevation)

        elevation_diff = elevations[-1] - elevations[0]
        terrain_type = ''
        if elevation_diff > 1000:
            terrain_type = 'Горы'
        elif elevation_diff > 500:
            terrain_type = 'Холмы'
        elif elevation_diff > 250:
            terrain_type = 'Пересеченная'
        elif elevation_diff > 0:
            terrain_type = 'Равнина'

        step_frequency = self.get_step(points, timestamps)

        latitude = points[0].latitude
        longitude = points[0].longitude
        datetime = timestamps[0]

        temperature, weather = self.get_weather(latitude, longitude, datetime)
        region = self.get_region(latitude, longitude)

        point_data = []
        for i in range(0, len(points), 150):
            group_points = points[i:i + 150]
            objects = self.get_poi(group_points[0].latitude, group_points[0].longitude)
            for point in group_points:
                point_data.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'elevation': point.elevation,
                    'temperature': temperature,
                    'weather': weather,
                    'terrain_type': terrain_type,
                    'poi_objects': objects,
                    'step_frequency': step_frequency,
                    'region': region,
                    'datetime': point.time,
                    'season': self.get_season(point.time),
                    'year': point.time.year,
                    'month': point.time.month,
                    'day': point.time.day,
                    'week_day': pd.to_datetime(point.time).weekday(),
                    'time_of_day': self.get_time_of_day(point.time.hour)
                })

        data = {
            'temperature': temperature,
            'elevation': max(elevations),
            'weather': weather,
            'terrain_type': terrain_type,
            'step_frequency': step_frequency,
            'region': region,
            'datetime': datetime,
            'season': self.get_season(datetime),
            'year': datetime.year,
            'month': datetime.month,
            'day': datetime.day,
            'week_day': pd.to_datetime(datetime).weekday(),
            'time_of_day': self.get_time_of_day(datetime.hour),
            'gpx_data': gpx
        }
        return data, point_data

    def check_track_id(self, region, datetime):
        conn = pymysql.connect(user='root', password='', port=3306, host='MySQL-8.0', database='track_db2')
        cursor = conn.cursor()
        cursor.execute('SELECT track_id FROM track WHERE region = %s AND datetime = %s', (region, datetime))
        id = cursor.fetchone()
        conn.close()
        return id

    def save_data(self, data, point_data):
        if self.check_track_id(data['region'], data['datetime']):
            print('Трек уже сохранен')
            return None
        conn = pymysql.connect(user='root', password='', port=3306, host='MySQL-8.0', database='track_db2')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO track (region, elevation, temperature, weather, terrain_type, 
                       step_frequency, datetime, season, gpx_data) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                       (data['region'], data['elevation'], data['temperature'], data['weather'], data['terrain_type'], data['step_frequency'],
                        data['datetime'].strftime('%Y-%m-%d %H:%M:%S'), data['season'], data['gpx_data']))
        track_id = cursor.lastrowid
        for point in point_data:
            cursor.execute('''INSERT INTO points (track_id, latitude, longitude, elevation, temperature,
                        weather, terrain_type, poi_objects, step_frequency, region, datetime, season, 
                        year, month, day, week_day, time_of_day) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s)''',
                           (track_id, point['latitude'], point['longitude'], point['elevation'], point['temperature'],
                        point['weather'], point['terrain_type'], str(point['poi_objects']), point['step_frequency'], point['region'],
                        point['datetime'], point['season'], point['year'], point['month'], point['day'], point['week_day'], point['time_of_day']))
        conn.commit()
        conn.close()

        self.create_map(point_data, track_id)

        df = []
        for point in point_data:
            df.append({
                'track_id': track_id,
                'latitude': point['latitude'],
                'longitude': point['longitude'],
                'elevation': point['elevation'],
                'temperature': point['temperature'],
                'weather': point['weather'],
                'terrain_type': point['terrain_type'],
                'poi_objects': str(point['poi_objects']),
                'step_frequency': point['step_frequency'],
                'region': point['region'],
                'datetime': point['datetime'],
                'season': point['season'],
                'year': point['year'],
                'month': point['month'],
                'day': point['day'],
                'week_day': point['week_day'],
                'time_of_day': point['time_of_day']
            })
        df = pd.DataFrame(df)
        old = pd.read_csv(self.dataset)
        df = pd.concat([df, old], ignore_index=True)
        df.to_csv(self.dataset)

if __name__ == '__main__':
    model = Modela()
    links = [
        'https://nasledniki.narod.ru/03_GPS/GPS_Sources/03_East_Sayan_Mountains/Mondy_peak_Huruma.gpx'
    ]
    for link in links:
        gpx_file = model.download_gpx(link)
        data, point_data = model.parse_gpx(gpx_file)
        model.save_data(data, point_data)
