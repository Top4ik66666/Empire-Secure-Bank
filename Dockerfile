# Используем легкую версию Python
FROM python:3.9-slim

# Устанавливаем системные зависимости для работы с базой Postgres
RUN apt-get update && apt-get install -y libpq-dev gcc

# Указываем рабочую папку внутри контейнера
WORKDIR /app

# Копируем список библиотек и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта (код, шаблоны и т.д.)
COPY . .

# Команда для запуска нашего приложения
CMD ["python", "app.py"]
