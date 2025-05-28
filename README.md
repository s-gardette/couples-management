# 🏠 Household Management App

A modern, modular household expense tracking application built with FastAPI, HTMX, and Tailwind CSS. Track expenses, manage budgets, and organize your household finances with ease.

## ✨ Features

- **Multi-user household management** - Connect multiple people to shared households
- **Expense tracking** - Track and categorize household expenses
- **Smart expense splitting** - Automatically split expenses among household members
- **Real-time updates** - HTMX-powered dynamic interface without page reloads
- **Modern UI** - Beautiful, responsive design with Tailwind CSS
- **Modular architecture** - Clean, maintainable codebase with separate modules

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (for production) or SQLite (for development)
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd couples-management
   ```

2. **Install dependencies**
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install project dependencies
   uv sync
   ```

3. **Setup environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

## 🧪 Testing

The project includes comprehensive tests for all modules:

### Quick Test Commands

```bash
# Run all tests (recommended)
python run_tests.py

# Run with pytest directly
uv run pytest tests/ -v

# Run with coverage report
python run_tests.py --coverage
# or
uv run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_main.py             # Main application tests
├── test_jwt_system.py       # JWT authentication system tests
├── test_password_security.py # Password security and validation tests
└── __init__.py              # Test package initialization
```

### Test Coverage

Current test coverage includes:
- ✅ **Main Application** (4 tests) - Health checks, static files, app configuration
- ✅ **JWT System** (20 tests) - Token creation, verification, blacklisting, refresh
- ✅ **Password Security** (13 tests) - Hashing, validation, strength checking
- ✅ **Security Utilities** (5 tests) - Token generation, email masking

**Total: 42 tests** - All passing ✅

## 🏗️ Architecture

The application follows a modular architecture:

```
app/
├── core/           # Shared utilities and base functionality
├── modules/        # Feature modules
│   ├── auth/       # Authentication and user management
│   ├── expenses/   # Expense tracking and management
│   └── ...         # Future modules (budgets, shopping, etc.)
├── templates/      # Jinja2 templates
├── static/         # Static assets (CSS, JS, images)
└── tests/          # Test modules
```

## 🛠️ Development

### Code Quality

The project uses several tools for code quality:

- **Ruff** - Linting, formatting, and import sorting
- **MyPy** - Type checking (planned)
- **Pytest** - Testing framework

Run all quality checks:
```bash
# Linting and formatting
uv run ruff check app tests
uv run ruff format app tests

# Run tests
python run_tests.py

# Type checking (when implemented)
uv run mypy app
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head
```

## 📚 API Documentation

When the application is running, visit:
- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

## 🔧 Configuration

Key environment variables (see `env.example` for full list):

- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Application secret key
- `JWT_SECRET_KEY` - JWT token secret
- `DEBUG` - Enable debug mode
- `CORS_ORIGINS` - Allowed CORS origins

## 📋 Development Status

### ✅ Completed
- [x] Project foundation and setup
- [x] Modular architecture implementation
- [x] Basic FastAPI application with health checks
- [x] Frontend setup with Tailwind CSS and HTMX
- [x] Configuration management
- [x] Comprehensive testing infrastructure
- [x] Authentication module (Phase 3)
  - [x] JWT token system with blacklisting
  - [x] Password security and validation
  - [x] User management services
  - [x] Auth API endpoints
  - [x] Frontend templates (login, register, profile)

### 🚧 In Progress
- [ ] Expense tracking module (Phase 4)

### 📅 Planned
- [ ] Budget management
- [ ] Shopping lists
- [ ] Chore tracking
- [ ] Mobile app (future)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Running Tests

Before submitting a PR, ensure all tests pass:
```bash
python run_tests.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- Enhanced with [HTMX](https://htmx.org/)
- Package management by [uv](https://github.com/astral-sh/uv)