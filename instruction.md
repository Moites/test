Запуск агентов

1. Установите zip файл из репозиторя test в вкладке <>code и download ZIP
2. Запустите терминал зажав сочетание клавиш win + x и выберите терминал
3. Если python не установлен введите команду для установки **winget install -e --id Python.Python.3.13**
4. Закройте и откройте заново терминал
4. Введите в терминал **Expand-Archive -Path .\Downloads\test-main.zip -DestinationPath .**
5. Перейдите в репозиторий проекта **cd test-main**
6. Создание виртуального окружения venv **python -m venv .venv**
7. Активация окружения **\.venv\Scripts\Activate.ps1**
8. Установка библиотек **pip install -r requirements.txt**
9. Запуск агента А **python AgentA.py**
