import pymysql
import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score

class ModelDash:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.create_dash()

    def clustering_kmeans(self, df):
        data = df[['temperature', 'elevation', 'latitude', 'longitude']]
        model = KMeans(n_clusters=3, random_state=42, init='k-means++')
        scaler = StandardScaler()
        X = scaler.fit_transform(data[['temperature', 'elevation']])
        model.fit(X)
        return model, X, data

    def clustering_DBSCAN(self, df):
        data = df[['temperature', 'elevation', 'latitude', 'longitude']]
        model = DBSCAN(min_samples=3)
        scaler = StandardScaler()
        X = scaler.fit_transform(data[['temperature', 'elevation']])
        model.fit(X)
        return model, X, data
    
    def risk_data(self, model, df):
        risk_data = df.copy()
        risk_data['cluster'] = model.labels_
        risk_data['risk_level'] = 'Средняя'
        sizec = risk_data['cluster'].value_counts()
        smalest = sizec.nsmallest(2).index
        for i, cluster_id in enumerate(smalest):
            risk = 'Низкая' if i == 0 else 'Высокая'
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

    def get_evacuation_level(self, row):
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
        conn = pymysql.connect(host='MySQL-8.0', port=3306, user='root', password='', database='track_db')
        cursor = conn.cursor()
        cursor.execute('''SELECT DISTINCT region FROM tracks''')
        regions_raw = cursor.fetchall()
        regions = [str(region[0]) for region in regions_raw if region[0]]
        cursor.execute('''SELECT COUNT(track_id) FROM tracks''')
        tracks = cursor.fetchone()[0]
        conn.close()

        self.app.layout = html.Div([
            html.H1('Track Dashboard'),
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
                                     [{'label': time_of_day, 'value': time_of_day} for time_of_day in ['Утро', 'День', 'Вечер', 'Ночь']],
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
            conn = pymysql.connect(host='MySQL-8.0', port=3306, user='root', password='', database='track_db')
            track_df = pd.read_sql_query('SELECT * FROM tracks', conn)
            points_df = pd.read_sql_query('SELECT * FROM points', conn)
            filtered_df = track_df.copy()
            conn.commit()
            filtered_df['track_datetime'] = pd.to_datetime(filtered_df['datetime'])
            filtered_df['hour'] = filtered_df['track_datetime'].dt.hour
            filtered_df['time_of_day'] = pd.cut(filtered_df['hour'], bins=[0, 8, 12, 18, 24], labels=['Ночь', 'Утро', 'День', 'Вечер'], )
            if region != 'all':
                filtered_df = filtered_df[filtered_df['region'] == region]
            if time_of_day != 'all':
                filtered_df = filtered_df[filtered_df['time_of_day'] == time_of_day]

            season_data = filtered_df.groupby('season')['step_frequency'].mean().reset_index()
            fig1 = px.bar(season_data, x='season', y='step_frequency',
                          labels={'season': 'Сезон', 'step_frequency': 'Среднее количество шагов'},
                          color='step_frequency', title='Средняя частота шагов по сезонам')

            temp_time_of_day = filtered_df.groupby('time_of_day')['temperature'].mean().reset_index()
            fig2 = px.bar(temp_time_of_day, x='time_of_day', y='temperature',
                          labels={'time_of_day': 'Время суток', 'temperature': 'Температура'},
                          color='time_of_day')

            terrain_activity = filtered_df['terrain_type'].value_counts().reset_index()
            fig3 = px.pie(terrain_activity, names='terrain_type', values='count',
                          labels={'terrain_type': 'Тип местности', 'count': 'Количество'},
                          color='count')

            fig4 = px.scatter(filtered_df, x='elevation', y='step_frequency',
                              labels={'elevation': 'Высота', 'step_frequency': 'Частота шагов'},
                              color='step_frequency')

            fig5 = px.scatter(filtered_df, x='elevation', y='temperature',
                              labels={'elevation': 'Высота', 'temperature': 'Температура'},
                              color='temperature')

            region_activity = filtered_df['region'].value_counts().head(5).reset_index()
            fig6 = px.bar(region_activity, x='region', y='count',
                          labels={'region': 'Регионы', 'count': 'Количество'},
                          color='count')

            model, X, df = self.clustering_kmeans(points_df)
            risk_data = self.risk_data(model, df)

            fig7 = px.scatter(risk_data, x='elevation', y='temperature',
                              labels={'elevation': 'Высота', 'temperature': 'Температура',
                                      'risk_level': 'Уровень риска'},
                              color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'},
                              title='Кластеризация kmeans', color='risk_level')

            model_dbscan, X_dbscan, df_dbscan = self.clustering_DBSCAN(points_df)
            risk_datal_dbscan = self.risk_data(model_dbscan, df_dbscan)

            fig8 = px.scatter(risk_datal_dbscan, x='elevation', y='temperature',
                              labels={'elevation': 'Высота', 'temperature': 'Температура',
                                      'risk_level': 'Уровень риска'},
                              color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'},
                              title='Кластеризация DBSCAN', color='risk_level')

            points_df['risk_level'] = points_df.apply(self.get_risk_level, axis=1)
            points_df['evac_level'] = points_df.apply(self.get_evacuation_level, axis=1)
            points_df['flood_level'] = points_df.apply(self.get_flood, axis=1)
            points_df['fire_level'] = points_df.apply(self.get_fire_danger, axis=1)

            fig9 = px.scatter_map(points_df, lat='latitude', lon='longitude',
                                     labels={'latitude': 'Ширина', 'longitude': 'Долгота',
                                             'risk_level': 'Уровень риска'},
                                     color_discrete_map={'Низкая': 'green', 'Средняя': 'yellow', 'Высокая': 'red'},
                                     title='Интерактивная карта', color='risk_level',
                                  hover_data=['risk_level', 'evac_level', 'flood_level', 'fire_level'], zoom=8)
            fig9.layout.update(mapbox_style='open-street-map')

            silhouette = silhouette_score(X, model.labels_)
            calinski_harabasz = calinski_harabasz_score(X, model.labels_)
            metric = html.Div(f'''
                        silhouette: {silhouette:.3f}
                        calinski-harabasz: {calinski_harabasz:.1f}''')

            return fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, metric

    def start_dash(self):
        self.app.run(debug=True, port=8053)

if __name__ == '__main__':
    model = ModelDash()
    model.start_dash()