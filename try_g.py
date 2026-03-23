import pandas as pd
import sqlite3 
import os 
import pickle
import json
import numpy as np
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier 
from sklearn.metrics import accuracy_score, f1_score, recall_score
import matplotlib.pyplot as plt

class ModelV:
    # Конструктор
    def __init__(self):
        self.model_file = 'model.pkl'
        self.log_file = 'log.csv'
        self.version_file = 'version.json'
        self.check_file = 'check.txt'
        self.forecast_results_file = 'forecast.pkl'
        self.forecast_csv = 'forecast_data.csv'

    # Класификация для получения риска точки
    def get_risk(self, row):
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
        return level

    # Класификация для получения сложности эвакуации
    def get_evac(self, row):
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
        return level
    
    # Проверка на дрейф данных
    def check_drift(self, new_X, old_X):
        featers = []
        for column in new_X.columns:
            new_mean = new_X[column].mean()
            old_mean = old_X[column].mean()
            if abs(new_mean - old_mean) / max(abs(old_mean)) / 0.3:
                print(f'Дрифт в колонке {column}')
                featers.append(column)
        score = len(featers) / len(old_X)
        if score > 0.3:
            return True, score
        else:
            return False, score
    
    # Проверки появились ли новые данные
    def check_data(self, df):
        if os.path.exists(self.check_file):
            with open(self.check_file, 'rw') as f:
                old_len = len(int(f.read()))
                new_len = len(df)
                if new_len > old_len:
                    f.write(new_len)
                    return True
                else:
                    return False
        else:
            with open(self.check_file, 'w') as f:
                f.write(str(new_len))
            return True
        
    def forecast_cluster_changes(self):
        conn = sqlite3.connect('track_db.db', conn)
        df = pd.read_sql_query('SELECT * FROM points', conn)
        terrain_clusters = df.groupby('terrain_type')
        years = list(range(1, 11))
        forecast_data = []
        for terrain, group in terrain_clusters:
            avg_temp = group['temperature'].mean()
            avg_elev = group['elevation'].mean()  
            for year in years:
                future_temp = avg_temp + (0.2 * year)
                if avg_elev < 200:
                    flood_risk = 0.6 + (0.03 * year)
                elif avg_elev < 500:
                    flood_risk = 0.3 + (0.02 * year)
                else:
                    flood_risk = 0.1 + (0.01 * year)
                if future_temp > 20:
                    fire_risk = 0.5 + (0.04 * year)
                elif future_temp > 10:
                    fire_risk = 0.3 + (0.02 * year)
                else:
                    fire_risk = 0.1 + (0.01 * year)     
                forecast_data.append({
                    'terrain': terrain,
                    'year': year,
                    'temperature': future_temp,
                    'flood_risk': min(1.0, flood_risk),
                    'fire_risk': min(1.0, fire_risk)
                })
        forecast_df = pd.DataFrame(forecast_data)
        forecast_df.to_csv(self.forecast_csv, index=False)  
        with open(self.forecast_results_file, 'wb') as f:
            pickle.dump(forecast_df, f)
        self.visualize_forecast(forecast_df)
        return forecast_df

    def visualize_forecast(self, forecast_df):
        plt.figure(figsize=(12, 8))
        plt.subplot(2, 2, 1)
        for terrain in forecast_df['terrain'].unique():
            data = forecast_df[forecast_df['terrain'] == terrain]
            plt.plot(data['year'], data['flood_risk'], label=terrain)
        plt.title('Риск затопления')
        plt.xlabel('Год')
        plt.ylabel('Риск')
        plt.grid(True)
        plt.subplot(2, 2, 2)
        for terrain in forecast_df['terrain'].unique():
            data = forecast_df[forecast_df['terrain'] == terrain]
            plt.plot(data['year'], data['fire_risk'], label=terrain)
        plt.title('Пожароопасность')
        plt.xlabel('Год')
        plt.ylabel('Риск')
        plt.grid(True)
        plt.subplot(2, 2, 3)
        for terrain in forecast_df['terrain'].unique():
            data = forecast_df[forecast_df['terrain'] == terrain]
            plt.plot(data['year'], data['temperature'], label=terrain)
        plt.title('Температура')
        plt.xlabel('Год')
        plt.ylabel('°C')
        plt.grid(True)
        plt.subplot(2, 2, 4)
        year10 = forecast_df[forecast_df['year'] == 10]
        terrains = year10['terrain'].unique()
        x = range(len(terrains))
        plt.bar([i-0.2 for i in x], year10['flood_risk'].values, 0.4, label='Затопление')
        plt.bar([i+0.2 for i in x], year10['fire_risk'].values, 0.4, label='Пожар')
        plt.title('Риски на 10-й год')
        plt.xlabel('Тип местности')
        plt.ylabel('Риск')
        plt.xticks(x, terrains)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('forecast_plot.png')
        plt.show()

    # Обучение моделей и оценка по метрикам
    def start_model(self, X_train, X_test, y_train, y_test, model):
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred, zero_division=0, average='weighted'),
            'f1': f1_score(y_test, y_pred, zero_division=0, average='weighted')
        }
        return model, metrics
    
    # Получение лучшей модели
    def best_model(self, X_train, X_test, y_train, y_test, models):
        best_model = None
        best_score = 0
        best_metrics = None
        best_model_name = ''

        for model_name, model in models.items():
            trained_model, metrics = self.start_model(X_train, X_test, y_train, y_test, model)
            score = (metrics['accuracy'] + metrics['recall'] + metrics['f1']) / 3
            if score > best_score:
                best_model = trained_model
                best_metrics = metrics
                best_model_name = model_name
        print(best_model_name)
        return best_model_name, best_model, best_metrics
    
    # Получение текущей версии
    def get_version(self):
        if os.path.exists(self.version_file):
            with open(self.version_file, 'rb') as f:
                data = json.load(f)
                return data.get('version')
        else:
            return None
    
    # Сохранение данных о обучении
    def save_model(self, model_risk, model_evac, X, y_evac, y_risk, drift_score, reason, le_weather, le_terrain):
        version = self.get_version()
        if version == None:
            new_version = 1
        else:
            new_version = version + 1

        model_data = {
            'version': new_version,
            'model_risk': model_risk,
            'model_evac': model_evac,
            'y_evac': y_evac,
            'y_risk': y_risk,
            'X': X,
            'le_weather': le_weather,
            'le_terrain': le_terrain,
            'datetime': datetime.now().isoformat()
        }  
        with open(self.model_file, "wb") as f:
            pickle.dump(model_data, f)
        print('Модель сохранена')

        version_data = {
            'version': new_version,
            'reason': reason,
            'drift_score': drift_score,
            'datetime': datetime.now().isoformat()
        }
        with open(self.version_file, 'w') as f:
            json.dump(version_data, f)
        print('Версия сохранена')
        
        log_data = {
            'version': new_version,
            'reason': reason,
            'drift_score': drift_score,
            'datetime': datetime.now().isoformat()
        }

        log_df = pd.DataFrame([log_data])
        if os.path.exists(self.log_file):
            old_data = pd.read_csv(self.log_file)
            log_df = pd.concat([log_df, old_data], ignore_index=True)
        log_df.to_csv(self.log_file)
        print('Логи сохранены')

    # Создание моделей
    def model(self):
        df = pd.read_csv(self.dataset)

        le_weather = LabelEncoder()
        le_terrain = LabelEncoder()

        df['weather_encoded'] = le_weather.fit_transform(df['weather'])
        df['terrain_encoded'] = le_terrain.fit_transform(df['terrain_type'])

        df['risk_level'] = df.apply(self.get_risk, axis=1)
        df['evac_level'] = df.apply(self.get_evac, axis=1)

        X = df[['temperature', 'elevation', 'weather_encoded', 'terrain_encoded']]
        y_risk = df['risk_level']
        y_evac = df['evac_level']

        drift_score = 0
        reason = ''
        need_retrain = False

        if os.path.exists(self.model_file):
            with open(self.model_file, 'r') as f:
                old_data = pickle.load(f)
                need_retrain, drift_score = self.check_drift(X, old_data['X'])
                if need_retrain == True:
                    print('Дрейф в колонках требуется переобучение')
                    reason = 'Дрейф данных'
            need_retrain = self.check_data(df)
            if need_retrain == True:
                print('Новые данные требуется переобучение')
                reason = 'Новые данные'
        else:
            need_retrain = True
            print('Создание модели')
            reason = 'Создание модели'

        if need_retrain == True:
            X_train_risk, X_test_risk, y_train_risk, y_test_risk = train_test_split(X, y_risk, test_size=0.2, random_state=42)
            models = {
                'KNeighborsClassifier': KNeighborsClassifier(),
                'LogisticRegression': LogisticRegression(random_state=42),
                'RandomForestClassifier': RandomForestClassifier(random_state=42)
            }
            model_name_risk, model_risk, metrics_risk = self.best_model(X_train_risk, X_test_risk, y_train_risk, y_test_risk, models)

            X_train_evac, X_test_evac, y_train_evac, y_test_evac = train_test_split(X, y_evac, test_size=0.2, random_state=42)
            model_name_evac, model_evac, metrics_evac = self.best_model(X_train_evac, X_test_evac, y_train_evac, y_test_evac, models)

            print(f'Лучшая модель для риска прохождения: {model_name_risk} метрики: {metrics_risk}')
            print(f'Лучшая модель для сложности эвакуации: {model_name_evac} метрики: {metrics_evac}')

            if need_retrain or not os.path.exists(self.forecast_results_file):
                forecast = self.forecast_cluster_changes()
            else:
                with open(self.forecast_results_file, 'rb') as f:
                    forecast = pickle.load(f)
            
            self.save_model(model_risk, model_evac, X, y_evac, y_risk, drift_score, reason, le_weather, le_terrain)

if __name__ == '__main__':
    model = ModelV()
    model.model()