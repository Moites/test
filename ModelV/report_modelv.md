# Отчет по модулю В

## 1. Что делает система
- Определяет уровень риска маршрутов (Низкий/Средний/Высокий)
- Определяет сложность эвакуации
- Автоматически переобучается при новых данных
- Создает и сохраняет модели класификации и кластеризации

## 2. Используемые алгоритмы

### Класификация

- Random Forest
- Logistic Regression
- K-Nearest Neighbors

### Кластеризация

- Метод локтя

![Метод локтя](pictures/log.png)

- KMeans

![KMeans](pictures/clustering.png)

## 3. Метрики оценки
- Accuracy (точность)
- Precision (точность по классам)
- F1-score (сбалансированная метрика)

лучшая модель для risk: (RandomForestClassifier(random_state=42), {'accuracy': 1.0, 'precision': 1.0, 'f1': 1.0, 'avg_score': 1.0}, 'RandomForest')
лучшая модель для evacuation: (RandomForestClassifier(random_state=42), {'accuracy': 1.0, 'precision': 1.0, 'f1': 1.0, 'avg_score': 1.0}, 'RandomForest')

## 4. Непрерывное обучение
- Детекция дрифта данных
- Автопереобучение при изменениях
- Сохранение всех версий моделей

## 5. Файловая структура
 - model.pkl # текущая модель
 - version.json # история версий
 - log.csv # лог обучения
 - track_dataset.csv # данные