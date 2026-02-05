import pandas as pd
import os
import pickle
import json
from datetime import datetime
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder

class ModelPredict:
    def __init__(self):
        self.dataset = 'Files/track_dataset.csv'
        self.model_file = 'Files/model.pkl'
        self.log_file = 'Files/log.csv'
        self.version_file = 'Files/version.json'
        self.check_file = 'Files/check.txt'
        self.df = pd.read_csv(self.dataset, encoding='utf-8')
        self.df['datetime'] = pd.to_datetime(self.df['datetime'], format='mixed', utc=True)

    def get_risk_level(self, row):
        level = 0
        temp_str = str(row['temperature']).replace('[', '').replace(']', '')
        if row['elevation'] > 1000:
            level += 3
        elif row['elevation'] > 600:
            level += 2
        elif row['elevation'] > 300:
            level += 1
        if float(temp_str) < -10:
            level += 3
        elif float(temp_str)  < 0:
            level += 2
        elif float(temp_str)  < 10:
            level += 1
        if row['weather'][0]  == 'overcast':
            level += 1
        elif row['weather'][0]  == 'moderateDrizzle':
            level += 1
        elif row['weather'][0]  == 'heavySnowfall':
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
        temp_str = str(row['temperature']).replace('[', '').replace(']', '')
        if row['elevation'] > 1000:
            level += 2
        elif float(temp_str) > 500:
            level += 1
        if float(temp_str)  < -10:
            level += 2
        elif float(temp_str)  < 0:
            level += 1
        if row['weather'][0]  == 'overcast':
            level += 1
        elif row['weather'][0]  == 'moderateDrizzle':
            level += 1
        elif row['weather'][0]  == 'heavySnowfall':
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

    def check_drift(self, new_data, old_data, threshold):
        features = []
        for column in new_data.columns:
            if pd.api.types.is_numeric_dtype(new_data[column]):
                new_mean = new_data[column].mean()
                old_mean = old_data[column].mean()
                if abs(new_mean - old_mean) / max(abs(old_mean), 1) > threshold:
                    features.append(column)
                    print(f'дрифт данных в колонке {column}')
        drift_score = len(features) / len(old_data)
        if drift_score > threshold:
            print('Требуется переобучение')
            return True, drift_score
        return False, drift_score

    def check_data(self):
        if not os.path.exists(self.check_file):
            with open(self.check_file, 'w') as f:
                f.write(str(len(self.df)))
        with open(self.check_file, 'r') as f:
            content = int(f.read().strip())
        current_count = len(self.df)
        if current_count > content:
            with open(self.check_file, 'w') as f:
                f.write(str(len(self.df)))
            return True
        else:
            return False

    def start_model(self, model, X_train, X_test, y_train, y_test):
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(y_test, y_pred, average='weighted', zero_division=0),
        }
        return metrics, model

    def best_model(self, models, X_train, X_test, y_train, y_test):
        best_models_obj = None
        best_metrics = None
        best_model_name = ''
        best_avg_score = 0

        for model_name, model in models.items():
            metrics, trained_model = self.start_model(model, X_train, X_test, y_train, y_test)
            avg_score = (metrics['accuracy'] + metrics['f1'] + metrics['precision']) / 3
            if best_metrics is None or avg_score > best_avg_score:
                best_metrics = metrics
                best_metrics['avg_score'] = avg_score
                best_avg_score = avg_score
                best_models_obj = trained_model
                best_model_name = model_name

        return best_models_obj, best_metrics, best_model_name

    def get_version(self):
        if os.path.exists(self.version_file):
            with open(self.version_file, 'r') as f:
                version = json.load(f)
                return version['version']
        return None

    def save_model(self, best_risk, best_evac, le_weather, le_terrain, X, y_risk, y_evacuation, drift_score, reason):
        version = self.get_version()
        if version is None:
            new_version = 1
        else:
            new_version = version + 1

        model_data = {
            'version': new_version,
            'risk_model': best_risk,
            'evacuation_model': best_evac,
            'le_weather': le_weather,
            'le_terrain': le_terrain,
            'X': X,
            'y_risk': y_risk,
            'y_evacuation': y_evacuation,
            'datetime': datetime.now().isoformat(),
        }
        with open(self.model_file, 'wb') as f:
            pickle.dump(model_data, f)

        all_versions = {'version': new_version, 'versions': []}
        if os.path.exists(self.version_file):
            with open(self.version_file, 'r') as f:
                json.load(all_versions, f)

        all_versions['version'] = new_version
        version_data = {
            'version': new_version,
            'datetime': datetime.now().isoformat(),
            'reason': reason,
            'drift_score': drift_score
        }
        all_versions['versions'].append(version_data)
        with open(self.version_file, 'w') as f:
            json.dump(all_versions, f, indent=2)
        log_info = {
            'version': new_version,
            'datetime': datetime.now().isoformat(),
            'drift_score': drift_score,
            'reason': reason
        }
        log_df = pd.DataFrame([log_info])
        if os.path.exists(self.log_file):
            log = pd.read_csv(self.log_file)
            log_df = pd.concat([log_df, log], ignore_index=True)
        log_df.to_csv(self.log_file, index=False)

    def model(self):
        self.df['risk_level'] = self.df.apply(self.get_risk_level, axis=1)
        self.df['evacuation_level'] = self.df.apply(self.get_evacuation_level, axis=1)

        le_weather = LabelEncoder()
        le_terrain = LabelEncoder()

        self.df['weather_encoded'] = le_weather.fit_transform(self.df['weather'])
        self.df['terrain_encoded'] = le_terrain.fit_transform(self.df['terrain_type'])

        self.df['temperature'] = self.df['temperature'].apply(
        lambda x: float(str(x).replace('[', '').replace(']', '').replace('"', '').replace("'", '')))
        X = self.df[['temperature', 'elevation', 'weather_encoded', 'terrain_encoded']]
        y_risk = self.df['risk_level']
        y_evacuation = self.df['evacuation_level']

        need_retrain = False
        reason = ''
        drift_score = 0

        if os.path.exists(self.model_file):
            with open(self.model_file, 'rb') as f:
                old_model = pickle.load(f)
                retrain, drift_score = self.check_drift(X, old_model['X'], 0.3)
                if retrain == True:
                    need_retrain = True
                    reason = f'Дрифт данных {drift_score}'
            retrain = self.check_data()
            if retrain == True:
                need_retrain = True
                reason = 'Новые данные'
        else:
            need_retrain = True
            retrain = 'Создание модели'

        if need_retrain == True:
            X_train_risk, X_test_risk, y_train_risk, y_test_risk = (
                train_test_split(X, y_risk, test_size=0.2, random_state=42))
            models = {
                'RandomForest': RandomForestClassifier(random_state=42),
                'LogisticRegression': LogisticRegression(random_state=42),
                'KNeighbors': KNeighborsClassifier(),
            }
            best_risk = self.best_model(models, X_train_risk, X_test_risk, y_train_risk, y_test_risk)

            X_train_evac, X_test_evac, y_train_evac, y_test_evac = (
                train_test_split(X, y_evacuation, test_size=0.2, random_state=42))

            best_evac = self.best_model(models, X_train_evac, X_test_evac,
                                                                        y_train_evac, y_test_evac)
            print(f'лучшая модель для risk: {best_risk}')
            print(f'лучшая модель для evacuation: {best_evac}')

            self.save_model(best_risk, best_evac, le_weather, le_terrain, X, y_risk, y_evacuation, drift_score, reason)
        return need_retrain, reason

    def create_clustres(self):
        cluster_df = self.df.copy()
        X = cluster_df[['temperature', 'elevation']]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        kmeans = KMeans(n_clusters=3, random_state=42, init='k-means++')
        kmeans_lables = kmeans.fit_predict(X_scaled)

        cluster_df.loc[:, 'cluster'] = kmeans_lables

        wcss = []
        for i in range(1, 11):
            kmeans = KMeans(n_clusters=i, random_state=42, init='k-means++')
            kmeans.fit(X_scaled)
            wcss.append(kmeans.inertia_)
        plt.plot(range(1, 11), wcss)
        plt.xlabel('Number of clusters')
        plt.ylabel('WCSS')
        plt.show()

        y_pred = KMeans(n_clusters=3, random_state=42, init='k-means++').fit_predict(X_scaled)
        plt.scatter(X_scaled[:, 0], X_scaled[:, 1], c=y_pred)
        plt.title('K-Means')
        plt.show()

        return cluster_df, X_scaled, kmeans

if __name__ == '__main__':
    model = ModelPredict()
    need_retrain, reason = model.model()
    cluster_df, data, kmeans = model.create_clustres()
