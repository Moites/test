import dash
from dash import Input, Output, dcc, html
import pandas as pd
from datetime import datetime
import plotly.express as px
import requests
import numpy as np
import plotly.graph_objects as go

class DashAPI:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.df = pd.read_csv('Files/track_dataset.csv')
        self.api_url = 'http://127.0.0.1:8054/risk'

    def create_dash(self):
        self.app.layout = html.Div([
            html.H1('Визуализация рисков маршрутов'),
            html.Div([
                html.Label('Регион:'),
                dcc.Dropdown(
                    id='track_selector',
                    options=[{'label': region, 'value': region}
                             for region in self.df['region'].unique()],
                    placeholder='Выберите регион'
                )
            ]),
            html.Div([
                html.Label('Дата (YYYY-MM-DD):'),
                dcc.Input(
                    id='date_selector',
                    type='text',
                    value=datetime.now().strftime('%Y-%m-%d'),
                    style={'width': '150px'}
                )
            ]),
            html.Button('Анализировать', id='button'),
            dcc.Graph(id='risk_max'),
            html.Div(id='results')
        ])

        @self.app.callback(
            [Output('risk_max', 'figure'),
             Output('results', 'children')],
            [Input('button', 'n_clicks')],
            [dash.dependencies.State('track_selector', 'value'),
             dash.dependencies.State('date_selector', 'value')]
        )
        def update_dash(n_clicks, track_selector, date_selector):
            if n_clicks == 0 or not track_selector or not date_selector:
                return px.scatter(title='Выберите данные'), ''

            try:
                track_data = self.df[self.df['region'] == track_selector]
                if track_data.empty:
                    return px.scatter(title='Нет данных'), 'Трек не найден'

                predictions = []
                if len(track_data) > 100:
                    indices = np.linspace(0, len(track_data) - 1, 50, dtype=int)
                    track_data_sample = track_data.iloc[indices]
                else:
                    track_data_sample = track_data

                for _, row in track_data_sample.iterrows():
                    try:
                        payload = {
                            'latitude': float(row['latitude']),
                            'longitude': float(row['longitude']),
                            'elevation': float(row['elevation']),
                            'terrain_type': str(row['terrain_type']),
                            'track_date': f"{date_selector}T12:00:00"
                        }

                        response = requests.post(self.api_url, json=payload, timeout=20)
                        if response.status_code == 200:
                            predictions.append(response.json())
                    except:
                        continue

                if not predictions:
                    return px.scatter(title='Нет ответа от API'), 'API не ответил'

                df_pred = pd.DataFrame([
                    {
                        'latitude': p['coordinates']['latitude'],
                        'longitude': p['coordinates']['longitude'],
                        'risk': p['prediction']['risk'],
                        'evacuation': p['prediction']['evacuation'],
                        'temperature': p['factors']['temperature']
                    } for p in predictions
                ])

                fig = go.Figure()

                fig.add_trace(go.Scattermapbox(
                    mode="lines",
                    lon=df_pred['longitude'],
                    lat=df_pred['latitude'],
                    line=dict(width=2, color='blue'),
                    showlegend=False,
                    hoverinfo='none'
                ))

                fig = px.scatter_mapbox(
                    df_pred,
                    lon='longitude',
                    lat='latitude',
                    color='risk',
                    title=f'Риски в регионе {track_selector}',
                    hover_data=['evacuation', 'temperature'],
                    color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'}
                )

                fig.update_layout(mapbox_style='open-street-map')

                stats = f"""
                Регион: {track_selector}
                Дата: {date_selector}
                Проанализировано точек: {len(df_pred)}
                Распределение рисков: {df_pred['risk'].value_counts().to_dict()}
                """
                return fig, stats

            except Exception as e:
                return px.scatter(title='Ошибка'), f'Ошибка: {str(e)}'

if __name__ == '__main__':
    dash_app = DashAPI()
    dash_app.create_dash()
    dash_app.app.run(debug=True, port=8059)