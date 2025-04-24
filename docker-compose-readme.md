# Docker Compose Setup for Multilingual Chat Backend

This document provides instructions for running the backend component of the Multilingual Chat application using Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your system
- Hugging Face API key for AI model integration

## Environment Setup

1. Create a `.env` file in the same directory as your `docker-compose.yml` file with the following content:

```
DEBUG=0
SECRET_KEY=your_django_secret_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
```

Replace the placeholder values with your actual keys.

## Running the Backend Application

1. Navigate to the backend directory:

```bash
cd path/to/Technical_Test/back
```

2. Start the backend services:

```bash
docker-compose up -d
```

This will start the following services:
- Backend (Django) - accessible at http://148.113.181.101:8000
- Redis cache for background tasks and caching

3. To view logs:

```bash
docker-compose logs -f
```

4. To view logs from a specific service:

```bash
docker-compose logs -f backend
```

## Stopping the Application

To stop all services:

```bash
docker-compose down
```

To stop all services and remove volumes (this will delete the SQLite database):

```bash
docker-compose down -v
```

## Service Details

### Backend
- Port: 8000
- Technology: Django
- Database: SQLite (file-based, stored in a persistent Docker volume)
- Features: JWT authentication, AI chat integration with Hugging Face models, conversation management
- Configured to accept connections from frontend at http://148.113.181.101:3001

### Cache
- Port: 6379
- Technology: Redis 6
- Used for caching frequent AI responses and background task processing

## Troubleshooting

If you encounter issues:

1. Check if all containers are running:
```bash
docker-compose ps
```

2. Inspect container logs for errors:
```bash
docker-compose logs -f
```

3. Ensure your Hugging Face API key is correctly set in the `.env` file

4. To check if the API is working properly:
```bash
curl http://localhost:8000/api/health/
```

5. If you need to access the SQLite database directly, you can use the following command:
```bash
docker-compose exec backend sqlite3 /app/db/db.sqlite3
```
