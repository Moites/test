Запуск агентов

1. Установите zip файл из репозиторя test в вкладке <>code и download ZIP
2. Запустите терминал зажав сочетание клавиш win + x и выберите терминал
3. Введите в терминал **Expand-Archive -Path .\Downloads\test-main.zip -DestinationPath .**
4. Перейдите в репозиторий проекта **cd test-main**
5. Создание виртуального окружения venv **py -m venv .venv**
6. Активация окружения **.\.venv\Scripts\Activate.ps1**
7. Установка библиотек **pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --no-cache-dir**
8. Запуск агента А **py AgentA.py**