# ШАГ 1: Взять за основу готовый образ с Python 3.10
FROM python:3.13-slim

# Установите временную зону
RUN apt-get update && apt-get install -y tzdata
ENV TZ=Asia/Yekaterinburg 
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ШАГ 2: Установить рабочую директорию внутри контейнера
WORKDIR /app

# ШАГ 3: Скопировать файл с зависимостями в контейнер
COPY requirements.txt .

# ШАГ 4: Установить все зависимости с помощью pip
RUN pip install -r requirements.txt

# ШАГ 5: Скопировать весь код нашего приложения (файл main.py)
COPY . .

# ШАГ 6: Указать команду, которая запустит приложение, когда контейнер стартует (то, что ты вводишь при запуске своего приложения в терминале)
CMD ["python", "main.py"]