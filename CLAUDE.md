# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Frontend (React + Vite)
```bash
cd frontend
npm run dev          # Start development server
npm run build        # Build for production
npm run lint         # Run ESLint
npm run preview      # Preview production build
```

### Backend (FastAPI + Python)
```bash
cd backend
uvicorn main:app --reload    # Start development server
python main.py               # Alternative startup

# Scripts de développement
python dev_reset_users.py    # Reset complet de la base de données (utilisateurs et données)
python migrate_oauth_columns.py  # Migration des colonnes OAuth
python create_tables.py      # Création/mise à jour des tables
```

### Full Project Start
```bash
start_project.bat    # Windows batch file that starts both frontend and backend
```

## Architecture Overview

This is a full-stack property management application with two main components:

### Backend (FastAPI)
- **main.py**: Main API routes and application entry point
- **models.py**: SQLAlchemy models defining database schema
- **schemas.py**: Pydantic schemas for request/response validation
- **database.py**: Database connection and session management
- **auth.py**: Authentication utilities (JWT tokens, password hashing, session management)
- **oauth_service.py**: OAuth authentication service with SOLID principles (Google, Facebook)
- **audit_logger.py**: Comprehensive logging system for all backend actions
- **middleware.py**: Custom middleware for request auditing

### Frontend (React + Vite)
- **src/pages/**: Main application pages (Login, Buildings, Apartments, etc.)
- **src/components/**: Reusable UI components (Cards, Forms, Navigation)
- **src/context/**: React contexts (AuthContext, ThemeContext)
- **src/services/api.js**: Axios configuration with JWT interceptors

## Key Domain Models

The application manages property data with these core entities:
- **UserAuth**: User accounts with authentication
- **Building**: Physical buildings with location data
- **Apartment**: Individual units within buildings
- **Copro**: Condominium/property management entities
- **SyndicatCopro**: Property management companies
- **ApartmentUserLink**: Many-to-many relationship between users and apartments with roles (owner, gestionnaire, lecteur)

## Database Configuration

- Uses MariaDB/MySQL with PyMySQL driver
- Database URL: `mysql+pymysql://maria_user:monpassword@localhost/locappart_db`
- SQLAlchemy ORM with relationship mappings

## Authentication Flow

- JWT-based authentication with Bearer tokens
- Frontend stores tokens in localStorage (persistent) or sessionStorage (session-only)
- Cookie-based auto-login for "Remember Me" functionality
- API client automatically includes Authorization headers
- 401 responses trigger automatic logout and redirect to login

## API Conventions

- All API endpoints require authentication except `/login/` and `/signup/`
- CORS configured for localhost development (ports 5173, 52388)
- File uploads handled through `/upload-photo/` endpoint
- RESTful patterns with standard HTTP status codes

## Internationalization

- Uses react-i18next for translations
- Translation files in `src/locales/en/` and `src/locales/fr/`
- Supports French and English languages

## UI/UX Patterns

- Theme switching capability with ThemeContext
- Responsive design for mobile, tablet, and desktop
- Consistent card-based components (BuildingCard, ApartmentCard, etc.)
- Form validation with error message display

## OAuth Authentication System

### Backend Configuration
- **Google OAuth**: Requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables
- **Facebook OAuth**: Requires `FACEBOOK_CLIENT_ID` and `FACEBOOK_CLIENT_SECRET` environment variables  
- **Microsoft OAuth**: Requires `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_TENANT_ID` environment variables
- SOLID principles implementation with provider factory pattern
- Session uniqueness maintained (one user = one active session)
- Comprehensive audit logging for OAuth actions

### Frontend Integration
- **Google Login**: Redirect-based OAuth flow with authorization code
- **Facebook Login**: Redirect-based OAuth flow
- **Microsoft Login**: Redirect-based OAuth flow with Azure AD
- OAuth callback page handles all provider responses
- Persistent token storage for all OAuth users
- Seamless integration with existing auth context
- Available on both login and registration pages
- No deprecated event listeners (all redirect-based flows)

### OAuth Endpoints
- `GET /auth/{provider}/login`: Initiate OAuth flow (Google, Facebook, Microsoft)
- `GET /auth/{provider}/callback`: Handle OAuth callbacks for all providers
- Session management identical to email/password authentication
- Automatic account creation and migration support

## File Upload System

- Images stored in `backend/uploads/` directory
- Unique filename generation with user ID and timestamp
- Support for building and apartment photos
- Static file serving through FastAPI

## Development Notes

- Frontend dev server runs on port 5173
- Backend dev server runs on port 8000
- Uses Vite for fast development builds
- ESLint configured for code quality
- No TypeScript currently (pure JavaScript)

## Development Tools

### Database Reset (Testing)
```bash
cd backend
python dev_reset_users.py    # Supprime TOUS les utilisateurs et données associées
```
⚠️ **ATTENTION**: Ce script supprime TOUTES les données (utilisateurs, sessions, logs, immeubles, appartements, copros, photos) de façon irréversible. Uniquement pour les tests en développement.

### Development Endpoints
- `DELETE /dev/reset-users` - Reset complet de la base (mode dev uniquement)
- `GET /dev/stats` - Statistiques de la base de données (mode dev uniquement)

Ces endpoints ne fonctionnent qu'avec `ENVIRONMENT=development` dans le .env