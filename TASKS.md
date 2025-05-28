# Household Management App - Development Tasks

## Project Overview
A modular household expense tracking application that allows multiple people to connect, track, and manage shared household expenses. Built with FastAPI using a modular architecture, Jinja2 templates, HTMX for dynamic interactions, Tailwind CSS for modern UI, and PostgreSQL for data persistence.

## Architecture Overview
The application follows a modular architecture pattern:
- **Core Module**: Main application, shared utilities, and base functionality
- **Auth Module**: Authentication, authorization, and user management
- **Expenses Module**: Expense tracking, splitting, and analytics
- **Future Modules**: Budgets, Shopping Lists, Chores, etc.

## Phase 1: Project Foundation & Setup

### 1.1 Environment Setup
- [ ] **Create Python virtual environment**
  - Set up virtual environment using `uv`
  - Configure uv for fast dependency management

- [ ] **Install core dependencies**
  - FastAPI (web framework)
  - Uvicorn (ASGI server)
  - Jinja2 (templating engine)
  - SQLAlchemy (ORM)
  - Alembic (database migrations)
  - Psycopg2 (PostgreSQL adapter)
  - Pydantic (data validation)
  - Python-multipart (form handling)
  - Passlib[bcrypt] (password hashing)
  - PyJWT (JWT token handling)
  - Python-dotenv (environment variables)

- [ ] **Install frontend dependencies**
  - HTMX (via CDN or local)
  - Tailwind CSS (via CDN or build process)
  - Alpine.js (for additional interactivity)

- [ ] **Create pyproject.toml**
  - Configure uv project structure
  - Pin dependency versions for reproducibility
  - Include development dependencies (pytest, black, ruff, mypy)

- [ ] **Setup modular project structure**
  ```
  app/
  ├── __init__.py
  ├── main.py                 # FastAPI application entry point
  ├── config.py               # Global configuration settings
  ├── database.py             # Database connection and session
  ├── dependencies.py         # Global dependencies
  ├── exceptions.py           # Custom exceptions
  ├── middleware.py           # Custom middleware
  │
  ├── core/                   # Core module
  │   ├── __init__.py
  │   ├── models/             # Shared models
  │   │   ├── __init__.py
  │   │   ├── base.py         # Base model class
  │   │   └── mixins.py       # Model mixins
  │   ├── schemas/            # Shared schemas
  │   │   ├── __init__.py
  │   │   └── base.py
  │   ├── services/           # Core services
  │   │   ├── __init__.py
  │   │   └── base_service.py
  │   ├── utils/              # Utility functions
  │   │   ├── __init__.py
  │   │   ├── security.py
  │   │   ├── validators.py
  │   │   └── helpers.py
  │   └── routers/            # Core routes
  │       ├── __init__.py
  │       └── health.py       # Health check endpoints
  │
  ├── modules/                # Application modules
  │   ├── __init__.py
  │   │
  │   ├── auth/               # Authentication module
  │   │   ├── __init__.py
  │   │   ├── models/
  │   │   │   ├── __init__.py
  │   │   │   └── user.py
  │   │   ├── schemas/
  │   │   │   ├── __init__.py
  │   │   │   ├── user.py
  │   │   │   └── auth.py
  │   │   ├── services/
  │   │   │   ├── __init__.py
  │   │   │   ├── auth_service.py
  │   │   │   └── user_service.py
  │   │   ├── routers/
  │   │   │   ├── __init__.py
  │   │   │   ├── auth.py
  │   │   │   └── users.py
  │   │   ├── dependencies.py # Auth-specific dependencies
  │   │   └── exceptions.py   # Auth-specific exceptions
  │   │
  │   ├── expenses/           # Expenses module
  │   │   ├── __init__.py
  │   │   ├── models/
  │   │   │   ├── __init__.py
  │   │   │   ├── household.py
  │   │   │   ├── expense.py
  │   │   │   └── expense_share.py
  │   │   ├── schemas/
  │   │   │   ├── __init__.py
  │   │   │   ├── household.py
  │   │   │   ├── expense.py
  │   │   │   └── analytics.py
  │   │   ├── services/
  │   │   │   ├── __init__.py
  │   │   │   ├── household_service.py
  │   │   │   ├── expense_service.py
  │   │   │   ├── splitting_service.py
  │   │   │   └── analytics_service.py
  │   │   ├── routers/
  │   │   │   ├── __init__.py
  │   │   │   ├── households.py
  │   │   │   ├── expenses.py
  │   │   │   └── analytics.py
  │   │   ├── dependencies.py # Expense-specific dependencies
  │   │   └── exceptions.py   # Expense-specific exceptions
  │   │
  │   └── future_modules/     # Placeholder for future modules
  │       ├── budgets/
  │       ├── shopping/
  │       └── chores/
  │
  ├── templates/              # Jinja2 templates
  │   ├── base/               # Base templates
  │   │   ├── base.html       # Main base template
  │   │   ├── components/     # Reusable components
  │   │   │   ├── navbar.html
  │   │   │   ├── sidebar.html
  │   │   │   ├── flash.html
  │   │   │   └── pagination.html
  │   │   └── layouts/        # Layout templates
  │   │       ├── app.html    # Authenticated app layout
  │   │       └── auth.html   # Authentication layout
  │   ├── auth/               # Auth module templates
  │   │   ├── login.html
  │   │   ├── register.html
  │   │   ├── profile.html
  │   │   └── components/
  │   ├── expenses/           # Expenses module templates
  │   │   ├── dashboard.html
  │   │   ├── households/
  │   │   │   ├── list.html
  │   │   │   ├── create.html
  │   │   │   ├── detail.html
  │   │   │   └── settings.html
  │   │   ├── expenses/
  │   │   │   ├── list.html
  │   │   │   ├── create.html
  │   │   │   ├── detail.html
  │   │   │   └── edit.html
  │   │   ├── analytics/
  │   │   │   ├── dashboard.html
  │   │   │   └── reports.html
  │   │   └── components/
  │   │       ├── expense_card.html
  │   │       ├── split_calculator.html
  │   │       └── balance_widget.html
  │   └── errors/             # Error templates
  │       ├── 404.html
  │       ├── 500.html
  │       └── 403.html
  │
  ├── static/                 # Static files
  │   ├── css/
  │   │   ├── tailwind.css    # Tailwind CSS (compiled)
  │   │   └── custom.css      # Custom styles
  │   ├── js/
  │   │   ├── htmx.min.js     # HTMX library
  │   │   ├── alpine.min.js   # Alpine.js
  │   │   └── app.js          # Custom JavaScript
  │   ├── images/
  │   └── icons/              # SVG icons
  │
  └── tests/                  # Test modules
      ├── __init__.py
      ├── conftest.py         # Pytest configuration
      ├── core/               # Core module tests
      ├── auth/               # Auth module tests
      ├── expenses/           # Expenses module tests
      └── integration/        # Integration tests
  ```

### 1.2 Configuration Management
- [ ] **Create modular configuration system**
  - Core application settings
  - Module-specific configurations
  - Environment-based configuration loading
  - Database connection settings
  - JWT secret key configuration
  - CORS settings
  - Debug mode toggle
  - Static files configuration

- [ ] **Create .env.example file**
  - Template for environment variables
  - Documentation for each variable
  - Module-specific environment variables

### 1.3 Frontend Build System
- [ ] **Setup Tailwind CSS build process**
  - Configure Tailwind CSS with PostCSS
  - Create tailwind.config.js with custom theme
  - Setup build scripts for CSS compilation
  - Configure purging for production builds

- [ ] **Setup static asset management**
  - Configure FastAPI static file serving
  - Setup asset versioning for cache busting
  - Optimize asset loading strategies

## Phase 2: Core Module Development

### 2.1 Base Infrastructure
- [ ] **Create base model classes**
  - UUID primary key mixin
  - Timestamp mixin (created_at, updated_at)
  - Soft delete mixin
  - Base CRUD operations

- [ ] **Implement base service patterns**
  - Generic CRUD service class
  - Service dependency injection
  - Error handling patterns
  - Logging integration

- [ ] **Create shared utilities**
  - Validation helpers
  - Security utilities
  - Date/time helpers
  - String manipulation utilities

### 2.2 Database Foundation
- [ ] **Setup Alembic with modular migrations**
  - Configure Alembic for multi-module structure
  - Create migration templates
  - Setup migration naming conventions

- [ ] **Create database session management**
  - Connection pooling configuration
  - Session lifecycle management
  - Transaction handling patterns

### 2.3 Core API Infrastructure
- [ ] **Implement health check endpoints**
  - Application health status
  - Database connectivity check
  - Module status verification

- [ ] **Setup global middleware**
  - Request logging middleware
  - Error handling middleware
  - CORS middleware
  - Security headers middleware

## Phase 3: Auth Module Development

### 3.1 User Model & Database Schema
- [ ] **Design User model**
  - id (UUID primary key)
  - email (unique, required)
  - username (unique, required)
  - hashed_password (required)
  - first_name, last_name
  - avatar_url (optional)
  - email_verified (boolean)
  - is_active (boolean)
  - last_login_at (timestamp)
  - created_at, updated_at timestamps

- [ ] **Create user-related database tables**
  - Users table with constraints
  - Email verification tokens table
  - Password reset tokens table
  - User sessions table (optional)

### 3.2 Authentication System
- [ ] **Implement password security**
  - Bcrypt password hashing
  - Password strength validation
  - Password history tracking (optional)

- [ ] **Implement JWT token system**
  - Access token generation
  - Refresh token mechanism
  - Token blacklisting (optional)
  - Token payload customization

- [ ] **Create authentication dependencies**
  - Current user dependency
  - Optional user dependency
  - Admin user dependency
  - Email verified dependency

### 3.3 Auth Services
- [ ] **Implement AuthService**
  - User registration logic
  - Login/logout functionality
  - Token management
  - Password reset workflow

- [ ] **Implement UserService**
  - User profile management
  - User search and filtering
  - User activation/deactivation
  - Avatar upload handling

### 3.4 Auth API Endpoints
- [ ] **Authentication endpoints**
  - POST /auth/register - User registration
  - POST /auth/login - User authentication
  - POST /auth/logout - User logout
  - POST /auth/refresh - Token refresh
  - POST /auth/forgot-password - Password reset request
  - POST /auth/reset-password - Password reset confirmation

- [ ] **User management endpoints**
  - GET /auth/me - Current user profile
  - PUT /auth/profile - Update user profile
  - PUT /auth/password - Change password
  - POST /auth/avatar - Upload avatar
  - POST /auth/verify-email - Email verification

### 3.5 Auth Frontend Templates (Tailwind + HTMX)
- [ ] **Create authentication layout**
  - Clean, modern design with Tailwind
  - Responsive layout for mobile/desktop
  - Consistent branding and styling

- [ ] **Implement login page**
  - Beautiful login form with Tailwind styling
  - HTMX-powered real-time validation
  - Loading states and error handling
  - Remember me functionality
  - Social login placeholders

- [ ] **Implement registration page**
  - Multi-step registration form
  - Real-time field validation with HTMX
  - Password strength indicator
  - Email availability check
  - Terms and conditions acceptance

- [ ] **Create user profile management**
  - Profile information display
  - Inline editing with HTMX
  - Avatar upload with preview
  - Password change form
  - Account settings

## Phase 4: Expenses Module Development

### 4.1 Expenses Database Schema
- [ ] **Design Household model**
  - id (UUID primary key)
  - name (required)
  - description (optional)
  - invite_code (unique, for joining)
  - created_by (foreign key to User)
  - settings (JSON field for household preferences)
  - created_at, updated_at timestamps
  - is_active boolean flag

- [ ] **Design UserHousehold association model**
  - user_id (foreign key to User)
  - household_id (foreign key to Household)
  - role (enum: admin, member)
  - nickname (optional display name in household)
  - joined_at timestamp
  - is_active boolean flag

- [ ] **Design Expense model**
  - id (UUID primary key)
  - household_id (foreign key to Household)
  - created_by (foreign key to User)
  - title (required)
  - description (optional)
  - amount (decimal, required)
  - currency (default: USD)
  - category_id (foreign key to Category)
  - expense_date (date of expense)
  - receipt_url (optional)
  - tags (array of strings)
  - created_at, updated_at timestamps
  - is_active boolean flag

- [ ] **Design Category model**
  - id (UUID primary key)
  - household_id (foreign key to Household, nullable for global categories)
  - name (required)
  - icon (optional)
  - color (hex color code)
  - is_default (boolean)

- [ ] **Design ExpenseShare model**
  - id (UUID primary key)
  - expense_id (foreign key to Expense)
  - user_id (foreign key to User)
  - share_amount (decimal)
  - share_percentage (decimal, optional)
  - is_paid (boolean)
  - paid_at (timestamp, nullable)
  - payment_method (optional)

### 4.2 Expenses Services
- [ ] **Implement HouseholdService**
  - Household CRUD operations
  - Member management
  - Invite code generation and validation
  - Household settings management

- [ ] **Implement ExpenseService**
  - Expense CRUD operations
  - Expense filtering and search
  - Receipt upload handling
  - Expense categorization

- [ ] **Implement SplittingService**
  - Equal split calculation
  - Custom split algorithms
  - Percentage-based splitting
  - Split validation and recalculation

- [ ] **Implement AnalyticsService**
  - Spending summaries
  - Category analysis
  - User spending patterns
  - Balance calculations
  - Export functionality

### 4.3 Expenses API Endpoints
- [ ] **Household management endpoints**
  - POST /households - Create new household
  - GET /households - List user's households
  - GET /households/{id} - Get household details
  - PUT /households/{id} - Update household
  - DELETE /households/{id} - Delete household
  - POST /households/{id}/join - Join household by invite
  - POST /households/{id}/invite - Generate invite link
  - GET /households/{id}/members - List household members
  - PUT /households/{id}/members/{user_id} - Update member role
  - DELETE /households/{id}/members/{user_id} - Remove member

- [ ] **Expense management endpoints**
  - POST /households/{id}/expenses - Create expense
  - GET /households/{id}/expenses - List expenses (with filters)
  - GET /expenses/{id} - Get expense details
  - PUT /expenses/{id} - Update expense
  - DELETE /expenses/{id} - Delete expense
  - POST /expenses/{id}/receipt - Upload receipt
  - PUT /expenses/{id}/shares - Update expense splits
  - POST /expenses/{id}/shares/{user_id}/pay - Mark share as paid

- [ ] **Category management endpoints**
  - GET /households/{id}/categories - List categories
  - POST /households/{id}/categories - Create category
  - PUT /categories/{id} - Update category
  - DELETE /categories/{id} - Delete category

- [ ] **Analytics endpoints**
  - GET /households/{id}/analytics/summary - Spending summary
  - GET /households/{id}/analytics/categories - Category breakdown
  - GET /households/{id}/analytics/users - User spending analysis
  - GET /households/{id}/analytics/trends - Spending trends
  - GET /households/{id}/analytics/balances - Outstanding balances
  - GET /households/{id}/analytics/export - Export data

### 4.4 Expenses Frontend Templates (Tailwind + HTMX)
- [ ] **Create expenses dashboard**
  - Modern card-based layout with Tailwind
  - Expense summary widgets
  - Recent expenses list
  - Quick action buttons
  - Responsive design for all devices

- [ ] **Implement household management UI**
  - Household creation wizard with steps
  - Beautiful household cards with Tailwind
  - Member management interface
  - Invite system with QR codes
  - Settings panel with toggle switches

- [ ] **Create expense management interface**
  - Expense creation form with Tailwind styling
  - Multi-step expense wizard
  - Real-time split calculation with HTMX
  - Drag-and-drop receipt upload
  - Advanced filtering with HTMX updates

- [ ] **Implement expense list views**
  - Card and table view options
  - Infinite scroll with HTMX
  - Real-time search and filtering
  - Bulk actions with checkboxes
  - Sort and group options

- [ ] **Create analytics dashboard**
  - Interactive charts with Chart.js
  - Spending trend visualizations
  - Category breakdown with donut charts
  - User comparison charts
  - Export functionality

## Phase 5: Advanced HTMX + Tailwind Integration

### 5.1 Interactive Components
- [ ] **Create reusable HTMX components**
  - Auto-complete search inputs
  - Dynamic form fields
  - Modal dialogs with HTMX
  - Toast notifications
  - Loading states and skeletons

- [ ] **Implement advanced form handling**
  - Multi-step forms with progress indicators
  - Real-time validation with custom Tailwind styles
  - Dynamic field addition/removal
  - Form state persistence
  - Auto-save functionality

### 5.2 Real-time Features
- [ ] **Implement live updates**
  - Real-time expense list updates
  - Live balance calculations
  - Notification system
  - Activity feeds
  - Collaborative editing indicators

- [ ] **Create responsive interactions**
  - Smooth transitions with Tailwind
  - Hover effects and micro-interactions
  - Mobile-first touch interactions
  - Keyboard navigation support
  - Accessibility improvements

### 5.3 Performance Optimization
- [ ] **Optimize HTMX requests**
  - Request caching strategies
  - Debounced search inputs
  - Lazy loading for large lists
  - Optimistic UI updates
  - Error retry mechanisms

- [ ] **Optimize Tailwind CSS**
  - Purge unused CSS classes
  - Custom utility classes
  - Component extraction
  - Critical CSS inlining
  - CSS minification

## Phase 6: Testing & Quality Assurance

### 6.1 Unit Testing
- [ ] **Test core module**
  - Base model functionality
  - Utility functions
  - Service patterns
  - Configuration loading

- [ ] **Test auth module**
  - User model validation
  - Authentication logic
  - JWT token handling
  - Password security

- [ ] **Test expenses module**
  - Expense calculations
  - Splitting algorithms
  - Analytics computations
  - Data integrity

### 6.2 Integration Testing
- [ ] **Test module interactions**
  - Auth + Expenses integration
  - Cross-module dependencies
  - Database transactions
  - API endpoint flows

- [ ] **Test frontend interactions**
  - HTMX request/response cycles
  - Form submissions
  - Real-time updates
  - Error handling

### 6.3 End-to-End Testing
- [ ] **Test complete user workflows**
  - Registration to expense creation
  - Household management flows
  - Multi-user interactions
  - Mobile responsiveness

## Phase 7: Security & Performance

### 7.1 Security Implementation
- [ ] **Module-level security**
  - Input validation per module
  - Authorization boundaries
  - Data access controls
  - API rate limiting

- [ ] **Frontend security**
  - CSRF protection with HTMX
  - XSS prevention
  - Content Security Policy
  - Secure cookie handling

### 7.2 Performance Optimization
- [ ] **Database optimization**
  - Module-specific indexes
  - Query optimization
  - Connection pooling
  - Caching strategies

- [ ] **Frontend performance**
  - Tailwind CSS optimization
  - HTMX request optimization
  - Image optimization
  - Bundle size reduction

## Phase 8: Deployment & DevOps

### 8.1 Containerization
- [ ] **Update Docker configuration**
  - Multi-stage Dockerfile
  - Module-aware build process
  - Production optimizations
  - Health check endpoints

- [ ] **Create deployment scripts**
  - Database migration automation
  - Static asset compilation
  - Environment configuration
  - Monitoring setup

### 8.2 CI/CD Pipeline
- [ ] **Setup automated testing**
  - Module-specific test suites
  - Integration test automation
  - Frontend testing
  - Performance testing

- [ ] **Create deployment pipeline**
  - Automated builds
  - Environment promotions
  - Rollback strategies
  - Monitoring integration

## Phase 9: Documentation & Extensibility

### 9.1 Documentation
- [ ] **Module documentation**
  - Architecture overview
  - Module interaction diagrams
  - API documentation per module
  - Frontend component library

- [ ] **Developer guides**
  - Module development guidelines
  - Adding new modules
  - Tailwind + HTMX patterns
  - Testing strategies

### 9.2 Extensibility Framework
- [ ] **Module system enhancement**
  - Plugin architecture
  - Module discovery
  - Dynamic routing
  - Configuration management

- [ ] **Future module preparation**
  - Budget management module
  - Shopping list module
  - Chore management module
  - Calendar integration module

## Development Priorities

### Priority 1 (MVP - Core Functionality)
- Core module infrastructure
- Auth module (registration, login, profile)
- Basic expenses module (households, expenses, simple splitting)
- Essential Tailwind + HTMX templates
- Database setup and migrations

### Priority 2 (Enhanced Features)
- Advanced expense splitting
- Analytics dashboard
- Advanced HTMX interactions
- Mobile-responsive design
- Receipt upload functionality

### Priority 3 (Polish & Scale)
- Performance optimization
- Advanced security features
- Comprehensive testing
- Documentation
- Deployment automation

### Future Phases (Additional Modules)
- Budget management module
- Shopping list module
- Chore tracking module
- Calendar integration
- Mobile app API

This modular approach ensures scalability, maintainability, and allows for easy addition of new features while keeping the codebase organized and the UI modern with Tailwind CSS and HTMX.
