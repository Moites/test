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

with open('Files/model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('Files/version.json', 'rb') as f:
    version = json.load(f)

def get_weather_description(weather_code):
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
        response = requests.get(url, params=params, headers=headers, timeout=200)
        if response.status_code == 200:
            data = response.json()
            weather_code = data.get('daily').get('weathercode')[0]
            weather = get_weather_description(weather_code)
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
        try:
            if weather in le_weather.classes_:
                weather_code = le_weather.transform([weather])[0]
            else:
                weather_code = 0  # default
        except:
            weather_code = 0
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