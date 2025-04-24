FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE multilingual_chat_api.settings

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static directories and collect static files
RUN mkdir -p /app/static /app/staticfiles
# Install gunicorn explicitly
RUN pip install gunicorn
RUN python manage.py collectstatic --noinput

# Run gunicorn
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "multilingual_chat_api.wsgi:application"]
