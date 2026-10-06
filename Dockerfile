FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Estáticos servidos pelo whitenoise (as variáveis são só para o settings importar)
RUN DJANGO_SECRET_KEY=build DB_NAME=x DB_USER=x DB_PASSWORD=x \
    python manage.py collectstatic --noinput

EXPOSE 8000

# migrate aplica as migrations versionadas (schema + dados iniciais) no Postgres
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py bootstrap && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
