import pandas as pd
import numpy as np
import requests
import json
import pickle
import sqlite3
from pydantic import BaseModel
from datetime import datetime
import plotly.graph_objects as go
import dash
import plotly.express as px
from dash import dcc, html, Output, Input
from fastapi import FastAPI
import uvicorn
import threading

class TrackAPI(BaseModel):
    latitude: float
    longitude: float
    elevation: float
    terrain_type: str
    datetime_track: datetime

app_api = FastAPI()

with open('model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('version.json', 'rb') as f:
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
    while True:
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
            response = requests.get(url, params=params, headers=headers, timeout=500)
            if response.status_code == 200:
                data = response.json()
                weather_code = data.get('daily').get('weathercode')[0]
                weather = get_weather_description(weather_code)
                return data.get('daily').get('temperature_2m_max')[0], weather
        except Exception as e:
            print(f'Ошибка получения метеоданных {e}')

@app_api.get('/')
def root():
    return {
        'messege': 'FAST API TRACK MODELS',
        'endpoints': '/models: Оценка по координатам'
    }

@app_api.post('/models')
def models(request: TrackAPI):
    le_weather = model.get('le_weather')
    le_terrain = model.get('le_terrain')

    temperature, weather = get_weather(request.latitude, request.longitude, request.datetime_track)

    try:
        if weather in le_weather.classes_:
            weather_code = le_weather.transform([weather])[0]
        else: 
            weather_code = 0
    except:
        weather_code = 0
    
    try:
        if request.terrain_type in le_terrain.classes_:
            terrain_code = le_terrain.transform([request.terrain_type])[0]
        else: 
            terrain_code = 0
    except:
        terrain_code = 0

    data = pd.DataFrame({
        'temperature': [float(temperature)],
        'elevation':  [float(request.elevation)],
        'weather_encoded': [int(weather_code)],
        'terrain_encoded': [int(terrain_code)]
    })

    data_values = data.values

    risk_model = model.get('model_risk')[0]
    evac_model = model.get('model_evac')[0]
    predict_risk_num = risk_model.predict(data_values)[0]
    predict_evac_num = evac_model.predict(data_values)[0]

    risk_levels = {
        0: "Низкая", 1: "Низкая", 
        2: "Средняя", 3: "Средняя",
        4: "Высокая", 5: "Высокая", 6: "Высокая"
    }
    
    evac_levels = {
        0: "Легкая", 1: "Легкая",
        2: "Средняя", 3: "Средняя",
        4: "Сложная", 5: "Сложная"
    }

    predict_risk = risk_levels.get(int(predict_risk_num), "Низкая")
    predict_evac = evac_levels.get(int(predict_evac_num), "Легкая")

    return {
        'coordinates':{
            'latitude': request.latitude,
            'longitude': request.longitude
        },
        'predict':{
            'predict_risk': predict_risk,
            'predict_evac': predict_evac
        },
        'metadata':{
            'elevation':  request.elevation,
            'temperature': temperature,
            'weather': weather,
            'terrain_type': request.terrain_type
        }
    }

class Track_Dash:
    def __init__(self):
        self.api_url = 'http://127.0.0.1:8050/models'
        self.app_dash = dash.Dash(__name__)
    
    def create_dash(self):
        conn = sqlite3.connect('track_db.db')
        df = pd.read_sql_query('SELECT * FROM points', conn)
        self.app_dash.layout = html.Div([
            html.H1('Dashboard Risk Tracks'),
            html.Div([
                html.Label('Трек:'),
                dcc.Dropdown(id='select_track',
                             options=[{'label': region, 'value': region} for region in df['region'].unique()],
                             placeholder='Выберите трек')
            ]),
            html.Div([
                html.Label('Дата (YYYY-MM-DD):'),
                dcc.Input(id='select_data',
                        type='text',
                        value=datetime.now().isoformat())
            ]),
            html.Button('Анализировать', id='button'),
            dcc.Graph(id='interective_map'),
            html.Div(id='result')
        ])

        @self.app_dash.callback(
            [Output('interective_map', 'figure'),
             Output('result', 'children')],
            [Input('button', 'n_clicks')],
            [dash.dependencies.State('select_track', 'value'),
             dash.dependencies.State('select_data', 'value')]
        )

        def update_dash(n_clicks, select_track, select_data):
            if n_clicks == 0 or not select_track or not select_data:
                return px.scatter(title='Введите данные'), ''
            try:
                track_data = df[df['region'] == select_track]
                indexes = np.linspace(0, len(track_data) - 1, 30, dtype=int)
                track_data_mini = track_data.iloc[indexes]
                predictions = []
                for _, row in track_data_mini.iterrows():
                    try:
                        params = {
                            'latitude': float(row['latitude']),
                            'longitude': float(row['longitude']),
                            'elevation': float(row['elevation']),
                            'terrain_type': str(row['terrain_type']),
                            'datetime_track': select_data
                        }
                        response = requests.post(self.api_url, json=params, timeout=100)
                        if response.status_code == 200:
                            predictions.append(response.json())
                    except:
                        continue
                df_pred = pd.DataFrame([{
                    'latitude': p['coordinates']['latitude'],
                    'longitude': p['coordinates']['longitude'],
                    'predict_risk': p['predict']['predict_risk'],
                    'predict_evac': p['predict']['predict_evac']
                } for p in predictions])

                fig = go.Figure()

                fig = px.scatter_map(
                    df_pred,
                    lat='latitude',
                    lon='longitude',
                    color='predict_risk',
                    hover_data=['predict_risk', 'predict_evac'],
                    title='Карта анализа',
                    color_discrete_map={'Высокая': 'red', 'Средняя': 'yellow', 'Низкая': 'green'}
                )
                fig.update_layout(mapbox_style='open-street-map')

                stats = f'''
                Регион {select_track}
                Дата {select_data}
                '''

                return fig, stats
            except Exception as e:
                return px.scatter(title='ошибка'), f'Ошибка {e}'
            
def run_dash():
    agent = Track_Dash()
    agent.create_dash()
    agent.app_dash.run(port=8051)

def run_api():
    uvicorn.run(app_api, port=8050)

if __name__ == '__main__':
    api_thread = threading.Thread(target=run_api)
    dash_theard = threading.Thread(target=run_dash)

    api_thread.start()
    dash_theard.start()