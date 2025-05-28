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

Run the test suite:
```bash
uv run pytest
```

Run tests with coverage:
```bash
uv run pytest --cov=app
```

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

- **Black** - Code formatting
- **Ruff** - Linting and import sorting
- **MyPy** - Type checking
- **Pytest** - Testing

Run all quality checks:
```bash
uv run black app tests
uv run ruff check app tests
uv run mypy app
uv run pytest
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
- [x] Testing infrastructure

### 🚧 In Progress
- [ ] Authentication module
- [ ] Expense tracking module
- [ ] Database models and migrations

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Styled with [Tailwind CSS](https://tailwindcss.com/)
- Enhanced with [HTMX](https://htmx.org/)
- Package management by [uv](https://github.com/astral-sh/uv)