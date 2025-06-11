"""
Template context processors for global template variables.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request

from app.config import settings

logger = logging.getLogger(__name__)


def get_dev_context(request: Request) -> Dict[str, Any]:
    """
    Get development context variables for templates.
    This function automatically detects development mode and provides
    debug information without requiring manual setup in views.
    """
    # Determine if we're in development mode
    is_dev_mode = (
        settings.debug or 
        settings.environment.lower() in ['development', 'dev', 'local'] or
        os.getenv('ENVIRONMENT', '').lower() in ['development', 'dev', 'local'] or
        os.getenv('DEBUG', '').lower() in ['true', '1', 'yes']
    )
    
    # Debug logging for troubleshooting
    logger.debug(f"Dev context check - settings.debug: {settings.debug}, settings.environment: {settings.environment}")
    logger.debug(f"ENVIRONMENT env var: {os.getenv('ENVIRONMENT', 'NOT_SET')}")
    logger.debug(f"DEBUG env var: {os.getenv('DEBUG', 'NOT_SET')}")
    logger.debug(f"Computed dev_mode: {is_dev_mode}")
    
    context = {
        'dev_mode': is_dev_mode,
        'debug': settings.debug,
        'environment': settings.environment,
    }
    
    # Add additional dev info if in development mode
    if is_dev_mode:
        # Try to determine template name from request path
        template_name = _guess_template_name(request)
        
        context.update({
            'template_name': template_name,
            'request_method': request.method,
            'request_path': str(request.url.path),
            'request_query': str(request.url.query) if request.url.query else None,
            'timestamp': datetime.now().isoformat(),
            'settings_info': {
                'app_name': settings.app_name,
                'app_version': settings.app_version,
                'database_name': settings.database_name,
                'cors_origins': settings.cors_origins,
            }
        })
    
    return context


def _guess_template_name(request: Request) -> str:
    """
    Try to guess the template name based on the request path.
    This is a best-effort approach for debugging purposes.
    """
    path = request.url.path.strip('/')
    
    # Handle common patterns
    if not path or path == '/':
        return 'home.html'
    elif path == 'dashboard':
        return 'main/dashboard.html'
    elif path == 'login':
        return 'auth/login.html'
    elif path == 'register':
        return 'auth/register.html'
    elif path == 'profile':
        return 'auth/profile.html'
    elif path.startswith('expenses'):
        if 'edit' in path:
            return 'expenses/edit.html'
        elif 'create' in path:
            return 'expenses/create.html'
        elif path == 'expenses':
            return 'expenses/list.html'
        else:
            return 'expenses/detail.html'
    elif path.startswith('households'):
        if path == 'households':
            return 'households/list.html'
        else:
            return 'households/detail.html'
    elif path.startswith('admin'):
        return 'admin/dashboard.html'
    
    # Default fallback
    return f"{path.replace('/', '_')}.html"


class GlobalTemplateContext:
    """
    Global template context manager that automatically injects
    common variables into all template responses.
    """
    
    @staticmethod
    def get_context(request: Request, **additional_context) -> Dict[str, Any]:
        """
        Get the global template context for any template.
        
        Args:
            request: FastAPI request object
            **additional_context: Additional context variables to merge
            
        Returns:
            Dictionary containing all global template variables
        """
        # Start with development context
        context = get_dev_context(request)
        
        # Add common global variables
        context.update({
            'request': request,
            'config': settings,
            'app_name': settings.app_name,
            'app_version': settings.app_version,
        })
        
        # Merge any additional context provided
        context.update(additional_context)
        
        return context


# Convenience function for easy use in templates
def get_global_context(request: Request, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to get global template context.
    Use this in your route handlers instead of passing dev_mode manually.
    
    Example:
        from app.core.template_context import get_global_context
        
        @router.get("/some-route")
        async def some_route(request: Request):
            context = get_global_context(request, current_user=user, custom_var="value")
            return templates.TemplateResponse(request, "template.html", context)
    """
    return GlobalTemplateContext.get_context(request, **kwargs) 