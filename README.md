# Multilingual Chat API

A Django REST Framework backend API with support for English and Arabic languages, secure JWT authentication, and rate limiting.

## Features

- Secure endpoints for signup, login, and logout using JWT
- User language preference storage (English or Arabic)
- Storage for user details, chat histories, language preferences, and AI-generated user summaries
- Chat histories and summaries tagged with appropriate language
- SQLite database for data storage
- Rate limiting to prevent abuse
- Backend APIs return responses compatible with the user's language preference

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```
4. Start the development server:
   ```
   python manage.py runserver
   ```

## API Endpoints

### Authentication

- **POST /api/auth/register/**: Register a new user
  - Required fields: `username`, `password`, `password2`, `email`, `first_name`, `last_name`
  - Optional field: `language_preference` (default: 'en')

- **POST /api/auth/login/**: Login and get JWT tokens
  - Required fields: `username`, `password`

- **POST /api/auth/refresh/**: Refresh JWT token
  - Required field: `refresh`

- **POST /api/auth/logout/**: Logout and blacklist JWT token
  - Required field: `refresh`

### User Profile

- **GET /api/profile/**: Get user profile with language preference
- **PUT/PATCH /api/profile/**: Update user profile
  - Optional field: `language_preference`

### Chat Messages

- **GET /api/messages/**: Get all user messages
  - Optional query parameter: `language` to filter by language
- **POST /api/messages/**: Create a new message
  - Required field: `content`
  - Optional field: `is_user_message` (default: true)

### Conversations

- **GET /api/conversations/**: Get all user conversations
  - Optional query parameter: `language` to filter by language
- **POST /api/conversations/**: Create a new conversation
  - Required field: `title`

- **GET /api/conversations/{id}/**: Get a specific conversation
- **PUT/PATCH /api/conversations/{id}/**: Update a conversation
- **DELETE /api/conversations/{id}/**: Delete a conversation

### User Summaries

- **GET /api/summaries/**: Get all user summaries
  - Optional query parameter: `language` to filter by language
- **POST /api/summaries/**: Create a new user summary
  - Required field: `content`

- **GET /api/summaries/{id}/**: Get a specific user summary
- **PUT/PATCH /api/summaries/{id}/**: Update a user summary
- **DELETE /api/summaries/{id}/**: Delete a user summary

## Language Support

The API supports both English and Arabic languages. The language can be set in the following ways:

1. User profile language preference
2. Accept-Language HTTP header
3. Language query parameter for specific endpoints

## Authentication

The API uses JWT (JSON Web Token) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Anonymous users: 100 requests per day
- Authenticated users: 1000 requests per day
- Signup: 5 requests per hour
- Login: 10 requests per hour
