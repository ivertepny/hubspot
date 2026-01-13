# Використовуємо офіційний Python образ
FROM python:3.11-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо uv
RUN pip install --no-cache-dir uv

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файли залежностей
COPY pyproject.toml uv.lock ./

# Встановлюємо залежності
RUN uv sync --frozen

# Копіюємо весь проект
COPY . .

# Встановлюємо PATH для використання Python з віртуального середовища
ENV PATH="/app/.venv/bin:$PATH"

# Перевіряємо, що Django встановлено
RUN .venv/bin/python -c "import django; print(f'Django {django.__version__} installed')"

# Збираємо статичні файли (якщо потрібно)
# RUN /app/.venv/bin/python manage.py collectstatic --noinput
RUN /app/.venv/bin/python manage.py migrate --noinput

# Відкриваємо порт
EXPOSE 8000

# Команда для запуску сервера (використовуємо Python з .venv)
CMD [".venv/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]
