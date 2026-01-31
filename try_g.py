import json
import pandas as pd
from fastapi import FastAPI
import requests
import pickle
from pydantic import BaseModel
from datetime import datetime
import uvicorn

app = FastAPI(title='Risk API')

class Risk(BaseModel):
    latitude: float
    longitude: float
    elevation: float
    terrain_type: str
    track_date: datetime

with open('model/model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('model/version.json', 'rb') as f:
    version = json.load(f)

def get_weather_code(weather_code):
        map = {
            0: 'clearSky',
            1: 'mainlyClear',
            2: 'partlyCloudy',
            3: 'overcast',
            45: 'fog =',
            48: 'depositingRimeFog',
            51: 'lightDrizzle',
            53: 'moderateDrizzle',
            55: 'denseDrizzle',
            56: 'lightFreezingDrizzle',
            57: 'moderateOrDenseFreezingDrizzle',
            61: 'lightRain',
            63: 'moderateRain',
            65: 'heavyRain',
            66: 'lightFreezingRain',
            67: 'moderateOrHeavyFreezingRain',
            71: 'slightSnowfall',
            73: 'moderateSnowfall',
            75: 'heavySnowfall',
            77: 'snowGrains',
            80: 'slightRainShowers',
            81: 'moderateRainShowers',
            82: 'heavyRainShowers',
            85: 'slightSnowShowers',
            86: 'heavySnowShowers',
            95: 'thunderstormSlightOrModerate',
            96: 'thunderstormStrong',
            99: 'thunderstormHeavy'}
        return map.get(weather_code)


def get_weather(latitude, longitude, date):
    try:
        url = 'https://archive-api.open-meteo.com/v1/archive'
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'start_date': date.strftime('%Y-%m-%d'),
            'end_date': date.strftime('%Y-%m-%d'),
            'daily': 'temperature_2m_max,weathercode',
            'timezone': 'auto'
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(response.json())
        if response.status_code == 200:
            data = response.json()
            weather_code = data.get('daily').get('weathercode')[0]
            weather = get_weather_code(weather_code)
            return data.get('daily').get('temperature_2m_max')[0], weather
    except Exception as e:
        print(f'Ошибка получения метеоданных {e}')

@app.get('/')
def root():
    return {
        'message': 'Welcome to Risk API!',
        'endpoint': {'/risk': 'Оценка по координатам'},
    }

@app.post('/risk')
def risk(request: Risk):
    try:
        le_weather = model.get('le_weather')
        le_terrain = model.get('le_terrain')
        temperature, weather = get_weather(request.latitude, request.longitude, request.track_date)
        weather_code = le_weather.transform([weather])[0]
        terrain_code = le_terrain.transform([request.terrain_type])[0]
        zapros = pd.DataFrame({
            'temperature': [float(temperature)],
            'elevation': [float(request.elevation)],
            'weather_encoded': [int(weather_code)],
            'terrain_encoded': [int(terrain_code)]
        })
        risk_model = model.get('risk_model')[0]
        evac_model = model.get('evacuation_model')[0]
        prediction_risk = risk_model.predict(zapros)[0]
        prediction_evac = evac_model.predict(zapros)[0]

        return {
            'coordinates':{
                'latitude': request.latitude,
                'longitude': request.longitude,
            },
            'prediction': {
                'risk': prediction_risk,
                'evacuation': prediction_evac,
            },
            'factors': {
                'temperature': temperature,
                'elevation': request.elevation,
                'terrain': request.terrain_type,
                'weather': weather,
            }
        }
    except Exception as e:
        print(e)

if __name__ == '__main__':
    uvicorn.run(app, port=8054)