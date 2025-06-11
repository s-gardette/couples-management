"""
Enhanced template handling with automatic global context injection.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.core.template_context import get_global_context

logger = logging.getLogger(__name__)


class EnhancedTemplates(Jinja2Templates):
    """
    Enhanced Jinja2Templates that automatically injects global context
    including development variables, without requiring manual setup.
    """
    
    def TemplateResponse(
        self,
        request: Request,
        name: str,
        context: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background = None,
    ) -> HTMLResponse:
        """
        Create a template response with automatic global context injection.
        
        This method automatically adds development variables, settings,
        and other global context without requiring manual setup in each view.
        
        Args:
            request: FastAPI request object
            name: Template name
            context: Additional context variables (optional)
            status_code: HTTP status code
            headers: Additional headers
            media_type: Media type
            background: Background task
            
        Returns:
            HTMLResponse with the rendered template
        """
        # Start with global context (includes dev_mode automatically)
        global_context = get_global_context(request)
        
        # Merge user-provided context
        if context:
            global_context.update(context)
        
        # Override template_name if we can detect it better from the template file
        if name and 'template_name' in global_context:
            global_context['template_name'] = name
        
        # Call parent method with enhanced context
        return super().TemplateResponse(
            request=request,
            name=name,
            context=global_context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


# Create a global instance that can be imported anywhere
def create_enhanced_templates(directory: str = "templates") -> EnhancedTemplates:
    """
    Create an enhanced templates instance.
    
    Args:
        directory: Templates directory path
        
    Returns:
        EnhancedTemplates instance
    """
    return EnhancedTemplates(directory=directory)


# Default global instance
templates = create_enhanced_templates() 