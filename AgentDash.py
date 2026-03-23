import sqlite3
import pandas as pd
import dash
from dash import html, dcc, Output, Input
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
import plotly.express as px
from sklearn.metrics import silhouette_score, calinski_harabasz_score

class ModelA():
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.create_dash()

    def clustering_KMEANS(self, df):
        data = df[['temperature', 'elevation']]
        model = KMeans(n_clusters=3, init='k-means++', random_state=42)
        scaler = StandardScaler()
        X = scaler.fit_transform(data[['temperature','elevation']])
        model.fit(X)
        return model, data, X
    
    def clustering_DBSCAN(self, df):
        data = df[['temperature', 'elevation']]
        model = DBSCAN(min_samples=3)
        scaler = StandardScaler()
        X = scaler.fit_transform(data[['temperature','elevation']])
        model.fit(X)
        return model, data
    
    def risk_data(self, model, df):
        risk_data = df.copy()
        risk_data['cluster'] = model.labels_
        risk_data['risk_level'] = 'Средняя'
        sizec = risk_data['cluster'].value_counts()
        smalest = sizec.nsmallest(2).index
        for i, cluster_id in enumerate(smalest):
            risk = 'Низкая' if i==0 else 'Высокая'
            risk_data.loc[risk_data['cluster'] == cluster_id, 'risk_level'] = risk
        return risk_data
    
    def get_risk_level(self, row):
        level = 0
        if row['elevation'] > 1000:
            level += 3
        elif row['elevation'] > 600:
            level += 2
        elif row['elevation'] > 300:
            level += 1
        if row['temperature'] < -10:
            level += 3
        elif row['temperature'] < 0:
            level += 2
        elif row['temperature'] < 10:
            level += 1
        if row['weather'] == 'overcast':
            level += 1
        elif row['weather'] == 'moderateDrizzle':
            level += 1
        elif row['weather'] == 'heavySnowfall':
            level += 2
        if row['terrain_type'] == 'Горы':
            level += 2
        elif row['terrain_type'] == 'Холмы':
            level += 1
        if level >= 6:
            return 'Высокая'
        elif level >= 3:
            return 'Средняя'
        else:
            return 'Низкая'
        
    def get_evac_level(self, row):
        level = 0
        if row['elevation'] > 1000:
            level += 2
        elif row['elevation'] > 500:
            level += 1
        if row['temperature'] < -10:
            level += 2
        elif row['temperature'] < 0:
            level += 1
        if row['weather'] == 'overcast':
            level += 1
        elif row['weather'] == 'moderateDrizzle':
            level += 1
        elif row['weather'] == 'heavySnowfall':
            level += 2
        if row['terrain_type'] == 'Горы':
            level += 2
        elif row['terrain_type'] == 'Холмы':
            level += 1
        if level >= 6:
            return 'Высокая'
        elif level >= 3:
            return 'Средняя'
        else:
            return 'Низкая'
        
    def get_flood(self, row):
        level = 0
        if row['elevation'] < 200:
            level += 2
        elif row['elevation'] < 500:
            level += 1
        if row['terrain_type'] == 'Равнина':
            level += 1
        if row['weather'] == 'Rain' or row['weather'] == 'Freezing Rain' or row['weather'] == 'Rain showers':
            level +=1 
        if 'Вода' in row['poi_objects']:
            level += 1
        if level >= 4:
            return 'Высокий'
        elif level >= 2:
            return 'Средний'
        else:
            return 'Низкий'
        
    def get_fire_danger(self, row):
        level = 0
        if row['elevation'] < 1000:
            level += 2
        elif row['elevation'] < 500:
            level += 1
        if row['terrain_type'] == 'Пересеченная':
            level += 1
        if row['weather'] == 'Clear sky' or row['weather'] == 'Mainly clear/partly cloudy/overcast':
            level +=1 
        if row['temperature'] > 30:
            level += 2
        elif row['temperature'] > 20:
            level += 1
        if 'Вода' in row['poi_objects']:
            level -= 1
        if 'Дерево' in row['poi_objects']:
            level += 1
        if level >= 5:
            return 'Высокий'
        elif level >= 3:
            return 'Средний'
        else:
            return 'Низкий'

    def create_dash(self):
        conn = sqlite3.connect('track_db.db')
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT region FROM tracks')
        regions = cur.fetchall()
        cur.execute('SELECT COUNT(track_id) FROM tracks')
        tracks = cur.fetchall()[0]
        conn.close()

        self.app.layout = html.Div([
            html.H1('Track dashboard'),
            html.Div([
                html.Label('Регион:'),
                dcc.Dropdown(id='select_region',
                            options=[{'label': 'Все регионы', 'value': 'all'}] + 
                            [{'label': region, 'value': region} for region in regions], 
                            value='all')
            ]),
            html.Div([
                html.Label('Время суток:'),
                dcc.Dropdown(id='select_time_of_day',
                            options=[{'label': 'Сутки', 'value': 'all'}] + 
                            [{'label': time_of_day, 'value': time_of_day} 
                            for time_of_day in ['Утро','День','Вечер','Ночь']], 
                            value='all')
            ]),
            html.Label('Общая статистика:'),
            html.Label(f'Всего треков: {tracks}'),
            html.Label(f'Всего регионов: {len(regions)}'),
            html.Div([
                dcc.Graph(id='avg_step_season'),
                dcc.Graph(id='temp_time_of_day'),
                dcc.Graph(id='terrain_activity'),
                dcc.Graph(id='elevation_step'),
                dcc.Graph(id='temp_step'),
                dcc.Graph(id='region_activity'),
                dcc.Graph(id='clustering_KMeans'),
                dcc.Graph(id='clustering_DBSCAN'),
                dcc.Graph(id='interactive_map'),
                html.Div(id='metrics')
            ])
        ])

        @self.app.callback(
            [Output('avg_step_season', 'figure'),
             Output('temp_time_of_day', 'figure'),
             Output('terrain_activity', 'figure'),
             Output('elevation_step', 'figure'),
             Output('temp_step', 'figure'),
             Output('region_activity', 'figure'),
             Output('clustering_KMeans', 'figure'),
             Output('clustering_DBSCAN', 'figure'),
             Output('interactive_map', 'figure'),
             Output('metrics', 'children')],
             [Input('select_region', 'value'),
              Input('select_time_of_day', 'value')]
        )

        def update_dash(region, time_of_day):
            conn = sqlite3.connect('track_db.db')
            points_df = pd.read_sql_query('SELECT * FROM points', conn)
            filtered_df = points_df.copy()
            conn.commit()
            filtered_df['track_datetime'] = pd.to_datetime(filtered_df['datetime'])
            filtered_df['hour'] = filtered_df['track_datetime'].dt.hour
            if region != 'all':
                filtered_df = filtered_df[filtered_df['region'] == region]
            if time_of_day != 'all':
                filtered_df = filtered_df[filtered_df['time_of_day'] == time_of_day]

            season_data = filtered_df.groupby('season')['step_frequncy'].mean().reset_index()
            fig1 = px.bar(season_data, 'season', 'step_frequncy', color='season', 
            labels={'season': 'Сезон', 'step_frequncy': 'Средняя частота шагов'},
            title='Средняя частота шагов по сезонам')

            temp_time_of_day = filtered_df.groupby('time_of_day')['temperature'].mean().reset_index()
            fig2 = px.bar(temp_time_of_day, 'time_of_day', 'temperature', color='time_of_day',
            labels={'time_of_day': 'Время суток', 'temperature': 'Температура'},
            title='Зависимость температуры от времени суток')

            terrain_activity = filtered_df['terrain_type'].value_counts().reset_index()
            fig3 = px.pie(terrain_activity, names='terrain_type', values='count', color='terrain_type', 
            labels={'terrain_type': 'Тип местности', 'count': 'Активность туристов'},
            title='Влияние типа местности на активность туристов')

            fig4 = px.scatter(filtered_df, 'elevation', 'step_frequncy', color='elevation',
            labels={'elevation': 'Высота', 'step_frequncy': 'Частота шагов'},
            title='Связь высоты маршрута с частотой шагов')

            fig5 = px.scatter(filtered_df, 'elevation', 'temperature', color='elevation',
            labels={'elevation': 'Высота', 'temperature': 'Температура'},
            title='Связь высоты маршрута с температурой')

            region_activity = filtered_df.groupby('season')['latitude'].value_counts().reset_index()
            fig6 = px.bar(region_activity, 'season', 'latitude', color='season',
            labels={'season': 'Сезон', 'latitude': 'Активность'},
            title='Наиболее популярные маршруты по периодам года')

            model_km, df_km, X_km = self.clustering_KMEANS(points_df)
            risk_data_km = self.risk_data(model_km, df_km)

            fig7 = px.scatter(risk_data_km, x='elevation', y='temperature',
            labels={'elevation': 'Высота', 'temperature': 'Температура', 
                    'risk_level': 'Уровень риска'},
                    color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'},
                    title='Кластеризация KMEANS', color='risk_level')
            
            model_db, df_db = self.clustering_DBSCAN(points_df)
            risk_data_db = self.risk_data(model_db, df_db)

            fig8 = px.scatter(risk_data_db, x='elevation', y='temperature',
            labels={'elevation': 'Высота', 'temperature': 'Температура', 
                    'risk_level': 'Уровень риска'},
                    color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'},
                    title='Кластеризация KMEANS', color='risk_level')
            
            points_df['risk_level'] = points_df.apply(self.get_risk_level, axis=1)
            points_df['evac_level'] = points_df.apply(self.get_evac_level, axis=1)
            points_df['flood_level'] = points_df.apply(self.get_flood, axis=1)
            points_df['fire_level'] = points_df.apply(self.get_fire_danger, axis=1)

            fig9 = px.scatter_map(points_df, lat='latitude', lon='longitude',
            labels={'latitude': 'Ширина', 'longitude': 'Долгота', 'risk_level': 'Уровнень опасности'},
            color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'},
            title='Интерактивная карта', color='risk_level', hover_data=['risk_level','evac_level','flood_level','fire_level'], zoom=8)
            fig9.layout.update(mapbox_style='open-street-map')

            silhouette =  silhouette_score(X_km, model_km.labels_)
            calinski_harabasz = calinski_harabasz_score(X_km, model_km.labels_)

            metrics = html.Div(f'''
                silhouette: {silhouette:.3f}
                calinski_harabasz: {calinski_harabasz:.1f}
            ''')

            return fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, metrics
        
    def start_dash(self):
        self.app.run(debug=True, port=8054)

if __name__ == '__main__':
    model = ModelA()
    model.start_dash()