from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLabel, QComboBox, QDateEdit, QPushButton, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl
from datetime import datetime
import requests
import numpy as np
import sys
import os
import tempfile
import folium
import subprocess
import pandas as pd

class AgentG(QMainWindow):
    def __init__(self):
        super().__init__()
        subprocess.Popen([sys.executable, "try_g.py"])
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)

        m = folium.Map(
            location=[55.7558 , 37.6173],
            zoom_start=6,
            tiles="OpenStreetMap",
            attr="OpenStreetMap"
        )

        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".html",
            mode="w",
            encoding="utf-8"
        )
        m.save(self.temp_file.name)
        self.temp_file.close()

        self.webView = QWebEngineView()
        settings = self.webView.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)

        self.webView.setUrl(QUrl.fromLocalFile(os.path.abspath(self.temp_file.name)))
        self.webView.setMinimumSize(800, 600)
        layout.addWidget(self.webView)

        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)

        label = QLabel("Регион:")
        layout.addWidget(label)
        self.combo = QComboBox()
        self.combo.addItems(self.df['region'].unique().tolist())
        layout.addWidget(self.combo)

        label = QLabel("Дата (YYYY-MM-DD):")
        layout.addWidget(label)
        self.date = QDateEdit()
        self.date.setDate(datetime.now())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy.MM.dd")
        layout.addWidget(self.date)

        button = QPushButton("Анализировать")
        button.clicked.connect(self.button_clicked)
        layout.addWidget(button)
        widget.setLayout(layout)

    def button_clicked(self):
        region = self.combo.currentText()
        date = self.date.date().toString("yyyy-MM-dd")

        try:
            df_filtered = self.df[self.df['region'] == region]
            if df_filtered.empty:
                self.stats_text.setText("Трек не найден")
                return
            
            predictions = []
            if len(df_filtered) > 100:
                indices = np.linspace(0, len(df_filtered) - 1, 50, dtype=int)
                df_filtered_sample = df_filtered.iloc[indices]
            else:
                df_filtered_sample = df_filtered

            for _, row in df_filtered_sample.iterrows():
                try:
                    payload = {
                        "latitude": float(row['latitude']),
                        "longitude": float(row['longitude']),
                        "elevation": float(row['elevation']),
                        "terrain_type": str(row['terrain_type']),
                        "track_date": f"{date}T12:00:00"
                    }

                    response = requests.post("http://127.0.0.1:8054/risk", json=payload, timeout=20)
                    if response.status_code == 200:
                        predictions.append(response.json())
                except Exception as e:
                    print(f"Ошибка запроса: {e}")
                    continue
            
            df_pred = pd.DataFrame([
                {
                'latitude': p['coordinates']['latitude'],
                'longitude': p['coordinates']['longitude'],
                'risk': p['prediction']['risk'],
                'evacuation': p['prediction']['evacuation'],
                'temperature': p['factors']['temperature']
                } for p in predictions
            ])

            self.create_risk_map(df_pred, region)
            
        except Exception as e:
            self.stats_text.setText(f"Ошибка: {str(e)}")

    def create_risk_map(self, df_pred, region):
        m = folium.Map(
            location=[df_pred['latitude'].mean(), df_pred['longitude'].mean()],
            zoom_start=8,
            tiles='OpenStreetMap'
        )

        colors = {
            'Низкая': 'green',
            'Средняя': 'orange',
            'Высокая': 'red'
        }

        for _, row in df_pred.iterrows():
            color = colors.get(row['risk'], 'blue')

            popun_text = f"""
            <b>Риск:</b> {row['risk']}<br>
            <b>Эвакуация:</b> {row['evacuation']}<br>
            <b>Температура:</b> {row['temperature']:.1f}*C
            """

            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=popun_text,
                color=color,
                fill=True,
                fillOpacity=0.7
            ).add_to(m)

        points = [[row['latitude'], row['longitude']] for _, row in df_pred.iterrows()]
        if len(points) > 1:
            folium.Polygon(
                points,
                weight=3,
                color='blue',
                opacity=0.5
            ).add_to(m)

        m.save(self.temp_file.name)
        self.webView.setUrl(QUrl.fromLocalFile(os.path.abspath(self.temp_file.name)))

    def close_event(self, event):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AgentG()
    window.setWindowTitle("Визуализация рисков маршрутов")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())