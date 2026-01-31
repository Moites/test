import os
import numpy as np
import pandas as pd
import gpxpy
import requests
import geopandas as gpd
from PIL import Image, ImageEnhance
from shapely.geometry import LineString
import matplotlib.pyplot as plt
import contextily as ctx
import pymysql

class ModelA:
    def __init__(self):
        self.dataset = 'track_dataset.csv'
        self.create_dataset()

    def create_dataset(self):
        if not os.path.exists(self.dataset):
            df = pd.DataFrame(columns=['track_id', 'region', 'datetime', 'weak_day',
            'season', 'year', 'month', 'day', 'time_of_day', 'temperature', 'weather', 'terrain_type', 'step_frequency',
            'latitude', 'longitude', 'elevation'])
            df.to_csv(self.dataset, index=False, encoding='utf-8')

    def download_gpx(self, link):
        try:
            response = requests.get(link)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f'Ошибка установки gpx файла {e}')

    def get_season(self, date):
        map = {
            1: 'Зима',
            12: 'Зима',
            11: 'Зима',
            10: 'Весна',
            9: 'Весна',
            8: 'Весна',
            7: 'Лето',
            6: 'Лето',
            5: 'Лето',
            4: 'Осень',
            3: 'Осень',
            2: 'Осень'
        }
        return map.get(date.month)

    def get_step_frequency(self, timestamps, points):
        sort = sorted(timestamps)
        total_seconds = (sort[-1] - sort[0]).total_seconds()
        step_frequency = (len(points) / total_seconds) * 60
        return round(step_frequency, 1)

    def get_region(self, latitude, longitude):
        try:
            url = 'https://nominatim.openstreetmap.org/reverse'
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'accept-language': 'ru',
                'zoom': 8
            }
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.3'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                country = data.get('address').get('country')
                region = data.get('name')
                return region, country
        except Exception as e:
            print(f'Ошибка получения региона {e}')

    def get_weather_code(self, code):
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

    def get_weather(self, latitude, longitude, date):
        try:
            url = 'https://api.open-meteo.com/v1/forecast'
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'start_date': date.strftime('%Y-%m-%d'),
                'end_date': date.strftime('%Y-%m-%d'),
                'daily': 'temperature_2m_max,weathercode',
                'timezone': 'auto'
            }
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, params=params, headers=headers, timeout=200)
            if response.status_code == 200:
                data = response.json()
                weather_code = data.get('daily').get('weathercode')[0]
                weather = self.get_weather_code(weather_code)
                return data.get('daily').get('temperature_2m_max')[0], weather
        except Exception as e:
            print(f'Ошибка получения метеоданных {e}')

    def get_poi_objects(self, latitude, longitude, radius=500):
        while True:
            try:
                url='https://overpass-api.de/api/interpreter'
                params = f'''[out:json][timeout:60];
                (
                node['building'](around:{radius},{latitude},{longitude});
                node['natural'='tree'](around:{radius},{latitude},{longitude});
                node['natural'='wood'](around:{radius},{latitude},{longitude});
                node['natural'='water'](around:{radius},{latitude},{longitude});
                node['highway'](around:{radius},{latitude},{longitude});
                node['amenity'='hospital'](around:{radius},{latitude},{longitude});
                );
                out body;'''
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.post(url, data={'data': params}, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    objects = []
                    for element in data.get('elements', []):
                        tags = element.get('tags', [])
                        if tags.get('natural') == 'tree' or tags.get('natural') == 'wood':
                            objects.append('Дерево')
                        elif tags.get('natural') == 'water':
                            objects.append('Вода')
                        elif tags.get('amenity') == 'hospital':
                            objects.append('Больница')
                        elif 'highway' in tags:
                            objects.append('Дороги')
                        elif 'building' in tags:
                            objects.append('Здание')
                    objects = list(set(objects))
                    return objects
                if response.status_code == 504 or response.status_code == 429:
                    continue
            except Exception as e:
                print(f'Ошибка получения объектов {e}')
    
    def get_week_date(self, week_code):
        map = {
            0: 'Понедельник',
            1: 'Вторник',
            2: 'Среда ',
            3: 'Четверг',
            4: 'Пятница',
            5: 'Суббота',
            6: 'Воскресенье'
        }
        return map.get(week_code)

    def create_map(self, points, track_id):
        filename = f'map{track_id}.jpg'
        line = LineString([(p['longitude'], p['latitude']) for p in points])
        gdf = gpd.GeoDataFrame(geometry=[line], crs='EPSG:4326')
        gdf = gdf.to_crs(epsg=3857)
        fig, ax = plt.subplots(figsize=(10, 8))
        gdf.plot(ax=ax, color='red', linewidth=2)
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
        ax.set_axis_off()
        plt.savefig(filename, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        img = Image.open(filename)
        base = filename.split('.')[0]
        img.rotate(10, fillcolor='white').save(f"{base}_rotated.jpg")
        arr = np.array(img)
        shifted = np.roll(arr, 30, axis=1)
        shifted[:, :30] = 255
        Image.fromarray(shifted).save(f"{base}_shifted.jpg")
        ImageEnhance.Brightness(img).enhance(1.2).save(f"{base}_bright.jpg")

    def parse_gpx(self, gpx):
        gpx_data = gpxpy.parse(gpx)
        points = []
        timestamps = []
        for track in gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append(point)
                    timestamps.append(point.time)

        elevations = [p.elevation for p in points if p.elevation is not None]
        elevations_max = max(elevations)
        elevations_min = min(elevations)

        track_datetime = pd.to_datetime(timestamps[0])

        latitude = points[0].latitude
        longitude = points[0].longitude

        elevation_diff = elevations_max - elevations_min
        terrain_type = ''
        if elevation_diff > 1000:
            terrain_type = 'Горы'
        elif elevation_diff > 500:
            terrain_type = 'Холмы'
        elif elevation_diff > 250:
            terrain_type = 'Пересеченная'
        elif elevation_diff > 0:
            terrain_type = 'Равнина'

        step_frequency = self.get_step_frequency(timestamps, points)
        region, country = self.get_region(latitude, longitude)
        temperature, weather = self.get_weather(latitude, longitude, track_datetime)

        track_points = []
        for i in range(0, len(points), 150):
            group_points = points[i:i + 150]
            if group_points:
                mid_index = len(group_points) // 2
                mid_point = points[mid_index]
                poi_objects = self.get_poi_objects(mid_point.latitude, mid_point.longitude)

                for point in group_points:
                    track_points.append({
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'elevation': point.elevation,
                        'point_datetime': point.time,
                        'season': self.get_season(point.time),
                        'year': point.time.year,
                        'month': point.time.month,
                        'day': point.time.day,
                        'weak_day': self.get_week_date(pd.to_datetime(point.time).weekday()),
                        'time_of_day': pd.cut([point.time.hour], bins=[0, 8, 12, 18, 24], labels=['Ночь', 'Утро', 'День', 'Вечер'])[0],
                        'poi_objects': poi_objects,
                        'temperature': temperature,
                    })

        return {
            'region': region,
            'country': country,
            'terrain_type': terrain_type,
            'temperature': temperature,
            'weather': weather,
            'latitude': latitude,
            'longitude': longitude,
            'elevation_max': elevations_max,
            'elevation_min': elevations_min,
            'step_frequency': step_frequency,
            'track_datetime': track_datetime,
            'season': self.get_season(track_datetime),
            'year': track_datetime.year,
            'month': track_datetime.month,
            'day': track_datetime.day,
            'weak_day': self.get_week_date(pd.to_datetime(track_datetime).weekday()),
            'time_of_day': pd.cut([track_datetime.hour], bins=[0, 8, 12, 18, 24], labels=['Ночь', 'Утро', 'День', 'Вечер'])[0],
            'gpx_data': gpx,
            'track_points': track_points,
        }

    def check_db(self, data):
        datetime_str = data['track_datetime'].strftime('%Y-%m-%d %H:%M:%S')
        conn = pymysql.connect(host='MySQL-8.0', port=3306, user='testsql', password='1234', database='track_db')
        cursor = conn.cursor()
        cursor.execute('''SELECT track_id FROM track WHERE region = %s AND track_datetime = %s''',
                       (data['region'], datetime_str))
        result = cursor.fetchone()
        conn.close()
        return result

    def save_data(self, data):
        if self.check_db(data):
            print(f'Трек уже сохранен')
            return None
        datetime_str = data['track_datetime'].strftime('%Y-%m-%d %H:%M:%S')

        conn = pymysql.connect(host='MySQL-8.0', port=3306, user='testsql', password='1234', database='track_db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO track (country, region, 
                track_datetime, season, gpx_data) VALUES (%s, %s, %s, %s, %s)''',
                       (data['country'], data['region'], datetime_str, self.get_season(data['track_datetime']), data['gpx_data']))
        track_id = cursor.lastrowid
        cursor.execute('''INSERT INTO metadata (track_id, temperature, weather, terrain_type, step_frequency, elevation)
                VALUES (%s, %s, %s, %s, %s, %s)''',
                       (track_id, data['temperature'], data['weather'], data['terrain_type'],
                        data['step_frequency'], data['elevation_max']))

        for point in data['track_points']:
            cursor.execute('''INSERT INTO track_point (track_id, latitude, longitude, elevation, point_datetime, 
            season, year, month, day, weak_day, time_of_day, poi_objects, temperature) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (track_id, point['latitude'], point['longitude'], point['elevation'], point['point_datetime'],
             point['season'], point['year'], point['month'], point['day'], point['weak_day'],
             point['time_of_day'], str(point['poi_objects']), point['temperature']))
        conn.commit()
        conn.close()

        self.create_map(data['track_points'], track_id)

        for point in data['track_points']:
            df = pd.DataFrame({
                'track_id': [track_id],
                'region': [data['region']],
                'datetime': point['point_datetime'],
                'season': [data['season']],
                'year': [data['year']],
                'month': [data['month']],
                'day': [data['day']],
                'weak_day': [data['weak_day']],
                'time_of_day': [data['time_of_day']],
                'temperature': [data['temperature']],
                'weather': [data['weather']],
                'terrain_type': [data['terrain_type']],
                'step_frequency': [data['step_frequency']],
                'elevation': point['elevation'],
                'latitude': point['latitude'],
                'longitude': point['longitude'],
                'poi_objects': [point['poi_objects']],
            })
            old_df = pd.read_csv(self.dataset)
            df = pd.concat([old_df, df], ignore_index=True)
            df.to_csv(self.dataset, index=False)

if __name__ == '__main__':
    m = ModelA()
    gpx_fails = [
        'https://www.openstreetmap.org/traces/12158994/data.gpx',
        'https://www.openstreetmap.org/traces/12158936/data.gpx'
    ]
    for link in gpx_fails:
        gpx = m.download_gpx(link)
        data = m.parse_gpx(gpx)
        test = m.save_data(data)