# 🏠 Household Management App

A modern, modular household expense tracking application built with FastAPI, HTMX, and Tailwind CSS. Track expenses, manage budgets, and organize your household finances with ease.

## ✨ Features

- **Multi-user household management** - Connect multiple people to shared households
- **Expense tracking** - Track and categorize household expenses
- **Smart expense splitting** - Automatically split expenses among household members
- **Real-time updates** - HTMX-powered dynamic interface without page reloads
- **Modern UI** - Beautiful, responsive design with Tailwind CSS
- **Modular architecture** - Clean, maintainable codebase with separate modules
- **Comprehensive logging** - Detailed application and access logs for monitoring

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
   
   **Option 1: Using the development script (recommended)**
   ```bash
   python run_server.py
   ```
   
   **Option 2: Using uvicorn directly**
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Open your browser**
   Navigate to `http://localhost:8000`

## 📝 Logging and Monitoring

The application includes comprehensive logging to help with development and debugging:

### Log Files

All logs are saved to the `logs/` directory with daily rotation:

- **`app_YYYYMMDD.log`** - Application logs (general activity, errors, debug info)
- **`error_YYYYMMDD.log`** - Error-only logs for quick issue identification
- **`access_YYYYMMDD.log`** - HTTP access logs (requests, responses, timing)
- **`uvicorn_YYYYMMDD.log`** - Uvicorn server logs

### Viewing Logs

Use the built-in log viewer for real-time monitoring:

```bash
# View application logs (default)
python view_logs.py

# View specific log types
python view_logs.py app      # Application logs
python view_logs.py error    # Error logs only
python view_logs.py access   # HTTP access logs
python view_logs.py uvicorn  # Server logs

# List all available log files
python view_logs.py list

# Show more lines initially
python view_logs.py app -n 100
```

The log viewer will show the last 50 lines by default and then follow new log entries in real-time (like `tail -f`).

### Development Scripts

- **`run_server.py`** - Development server with logging configuration
- **`view_logs.py`** - Real-time log viewer with filtering options

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
│   ├── logging.py  # Logging configuration
│   └── routers/    # Core API routes
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

### Development Workflow

1. **Start the development server:**
   ```bash
   python run_server.py
   ```

2. **Monitor logs in a separate terminal:**
   ```bash
   python view_logs.py app
   ```

3. **Run tests:**
   ```bash
   python run_tests.py
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
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `CORS_ORIGINS` - Allowed CORS origins

## 📋 Development Status

### ✅ Completed
- [x] Project foundation and setup
- [x] Modular architecture implementation
- [x] Basic FastAPI application with health checks
- [x] Frontend setup with Tailwind CSS and HTMX
- [x] Configuration management
- [x] Comprehensive testing infrastructure
- [x] Comprehensive logging system
- [x] Development tools and scripts
- [x] Authentication module (Phase 3)
  - [x] JWT token system with blacklisting
  - [x] Password security and validation
  - [x] User management services
  - [x] Auth API endpoints
  - [x] Frontend templates (login, register, profile)

### 🚧 In Progress
- [ ] Admin UI module implementation
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