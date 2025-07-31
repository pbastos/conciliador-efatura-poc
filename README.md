# Conciliador E-fatura POC

A web application for reconciling e-fatura records with bank movements, featuring intelligent matching algorithms and an intuitive user interface.

## Features

- Upload Excel files containing e-fatura records
- Upload Excel files containing bank movements
- Automatic matching based on:
  - Date (with configurable tolerance)
  - Amount (with percentage tolerance)
  - Description (fuzzy string matching)
- Manual confirmation/rejection of matches
- Export results to Excel
- Multi-tenant support

## Tech Stack

- **Frontend**: React with TypeScript, Ant Design
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **File Processing**: pandas, openpyxl

## Project Structure

```
conciliador-efatura-poc/
├── frontend/          # React TypeScript application
├── backend/           # FastAPI Python backend
├── database/          # Database migrations and seeds
└── docker-compose.yml # Development environment
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Docker and Docker Compose (for local development)
- Supabase account

### Environment Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SERVICE_KEY=your_service_key
   ```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Database Setup

1. Create a new Supabase project
2. Run migrations:
   ```bash
   cd database/migrations
   # Apply migrations through Supabase dashboard or CLI
   ```

## Development

### Running Tests

```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && pytest
```

### API Documentation

When the backend is running, visit:
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

## Deployment

See `deployment.md` for production deployment instructions.

## License

This is a proof of concept project.