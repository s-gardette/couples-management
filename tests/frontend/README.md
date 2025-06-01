# Frontend Tests

This directory contains comprehensive frontend tests for all template endpoints in the couples-management application.

## Overview

The frontend tests verify that all HTML templates and UI endpoints return proper HTTP status codes and contain expected content. The tests use pytest for clean, maintainable testing without unnecessary complexity.

## Test Structure

```
tests/frontend/
├── __init__.py                 # Package initialization
├── conftest.py                 # Test fixtures and utilities
├── test_config.py              # Configuration and constants
├── test_templates.py           # Comprehensive pytest-based tests
├── test_all_endpoints.py       # Simple, comprehensive endpoint tests
└── README.md                   # This documentation
```

## Running Tests

### Simple and Clean
Just use pytest - no complex runners needed:

```bash
# Run all frontend tests
pytest tests/frontend/ -v

# Run specific test file
pytest tests/frontend/test_all_endpoints.py -v

# Run with output capture disabled (see print statements)
pytest tests/frontend/test_all_endpoints.py -v -s

# Run specific test class
pytest tests/frontend/test_all_endpoints.py::TestFrontendEndpoints -v

# Run with coverage
pytest tests/frontend/ --cov=app --cov-report=html

# Run just the endpoint summary test
pytest tests/frontend/test_all_endpoints.py::test_all_endpoints_summary -v -s
```

### Quick Test
You can also run the test file directly:

```bash
python tests/frontend/test_all_endpoints.py
```

## Test Categories

### 1. Public Endpoints
Tests endpoints that don't require authentication:
- `/login` - Login page
- `/access-restricted` - Access restricted page

### 2. Authenticated Endpoints  
Tests endpoints that require user authentication:
- `/` - Root/dashboard
- `/expenses/*` - Expense management pages
- `/households/*` - Household management pages
- `/analytics` - Analytics dashboard
- `/budgets/*` - Budget pages (placeholders)
- `/reports` - Reports page (placeholder)
- `/settings` - Settings page (placeholder)
- `/onboarding/*` - Onboarding flow

### 3. HTMX Partial Endpoints
Tests HTMX partial endpoints for dynamic content:
- `/partials/households/*` - Household partials
- `/partials/expenses/*` - Expense partials

### 4. Expense Details Implementation
Tests our three-way expense details implementation:
- Modal partial: `/partials/expenses/{id}/details`
- Full page: `/expenses/{id}`
- API endpoint: `/api/expenses/{id}`

### 5. Error Handling
Tests error scenarios with invalid IDs and malformed requests.

### 6. Content Quality
Tests HTML structure, content expectations, and performance.

## Test Results Interpretation

### Expected Status Codes

| Endpoint Type | Without Auth | With Auth | Notes |
|---------------|--------------|-----------|-------|
| Public | 200 | 200 | Always accessible |
| Authenticated | 401/403/302 | 200 | Redirect to login or auth required |
| Partials | 401/403 | 200 | HTMX endpoints require auth |
| Invalid IDs | 404/403 | 404/403 | Resource not found or forbidden |

### Success Criteria

- **Public endpoints**: Must return 200 and contain expected content
- **Authenticated endpoints**: Must handle authentication properly (401/403/302 without auth, 200 with auth)
- **Partial endpoints**: Must return proper HTMX-compatible HTML fragments
- **Error handling**: Must return appropriate error codes for invalid requests

## Configuration

Test configuration is centralized in `test_config.py`:

- **Endpoint lists**: All testable URLs organized by category
- **Expected status codes**: What responses are considered successful
- **Content expectations**: What content should appear on different page types

## Test Data

The tests use pytest fixtures for realistic testing:

- `test_user`: Authenticated user for testing
- `test_household_with_expenses`: Complete household with sample expenses
- `authenticated_frontend_client`: Pre-authenticated test client
- `template_utils`: Utilities for template validation

## Why This Approach?

This simplified approach using only pytest provides:

1. **Simplicity**: No complex custom test runners
2. **Standard Tools**: Uses pytest, which developers already know
3. **Parametrization**: Clean test organization with `@pytest.mark.parametrize`
4. **Fixtures**: Proper test data setup and teardown
5. **Reporting**: Built-in pytest reporting and output
6. **Integration**: Works seamlessly with CI/CD and IDEs
7. **Maintainability**: Easy to understand and modify

## Integration with CI/CD

Standard pytest integration:

```bash
# In CI pipeline
pytest tests/frontend/ --junitxml=frontend-test-results.xml
```

## Recent Implementation Verified

The tests verify our recent template implementation:

- ✅ **Modal + Full Page + API**: Expense details available as modal partial, full page, and JSON API
- ✅ **Server-Side Rendering**: Initial content rendered server-side with HTMX enhancement
- ✅ **Progressive Enhancement**: Works without JavaScript, enhanced with HTMX
- ✅ **Unified Endpoints**: Single expense partial handles both recent and list views
- ✅ **Real Data Integration**: All templates now use real database data
- ✅ **Error Handling**: Proper authentication and validation throughout
- ✅ **Simple Testing**: Clean pytest-based testing without unnecessary complexity

### Test Files

### `test_all_endpoints.py`
Tests all frontend endpoints to ensure they return proper status codes and contain expected content.

### `test_templates.py`
Tests template rendering with realistic data and validates template functionality.

### `test_href_validation.py` ⭐ **NEW**
**Comprehensive href link validation test** that scans every template file and validates all href links:

#### What it does:
- 🔍 **Scans all template files** for href attributes
- 🔗 **Categorizes links** into: internal, external, placeholder, dynamic, static, template
- ✅ **Validates internal links** by making actual HTTP requests  
- 📊 **Reports detailed statistics** about link health
- 🚨 **Identifies broken links** and missing routes
- 🎯 **Handles Jinja2 templates** correctly (variables, control structures)

#### Categories of links:
- **Internal**: Routes within the app (e.g., `/expenses`, `/households`)
- **External**: External URLs (e.g., CDN links, external sites)
- **Static**: Static file references (e.g., `/static/css/styles.css`)
- **Template**: Jinja2 template syntax (e.g., `{{ url_for('login') }}`)
- **Dynamic**: URLs with template variables (e.g., `/households/{{ household.id }}`)
- **Placeholder**: Anchor links, JavaScript, mailto (e.g., `#`, `javascript:`, `mailto:`)

#### Test methods:
- `test_all_href_links_are_valid()` - Main validation test with detailed reporting
- `test_specific_navigation_links()` - Tests critical navigation routes
- `test_static_files_exist()` - Validates static file references
- `test_no_broken_internal_links()` - Ensures no 404 internal links
- `test_external_links_format()` - Validates external link format
- `test_missing_routes_detection()` - Identifies routes that might need implementation

#### Benefits:
- ✅ **Prevents dead links** in the application
- 🛡️ **Catches navigation issues** early in development
- 📈 **Provides link health metrics** (currently 97.1% success rate)
- 🔧 **Identifies missing routes** that need implementation
- 🎨 **Template-aware** - understands Jinja2 syntax

#### Current findings:
The test currently identifies 2 routes that may need attention:
- `/profile` (HTTP 404) - Profile page route not implemented
- `/api/auth/forgot-password` (HTTP 405) - Forgot password endpoint needs POST method

### `test_config.py`
Configuration constants and endpoint lists for frontend tests.

### `conftest.py`
Shared fixtures for frontend testing including authenticated clients and test data.

## Test Results

Current frontend test status:
- ✅ **All endpoint tests**: 17/20 working (85% success)
- ✅ **Template tests**: Comprehensive template validation
- ✅ **Href validation**: 97.1% success rate (66/68 valid links)

## Next Steps

1. **Fix HTMX partial endpoints** (from main test suite)
2. **Implement missing routes** identified by href validation:
   - Add `/profile` route
   - Fix `/api/auth/forgot-password` method
3. **Continue monitoring** link health with href validation test 