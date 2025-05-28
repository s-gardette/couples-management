"""
Additional model mixins for common functionality.
"""

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declared_attr


class NameMixin:
    """Mixin for models that have a name field."""

    @declared_attr
    def name(cls):
        return Column(String(255), nullable=False, index=True)


class DescriptionMixin:
    """Mixin for models that have a description field."""

    @declared_attr
    def description(cls):
        return Column(Text, nullable=True)


class ActiveMixin:
    """Mixin for models that have an active/inactive state."""

    @declared_attr
    def is_active(cls):
        return Column(Boolean, default=True, nullable=False, index=True)


class SlugMixin:
    """Mixin for models that have a URL-friendly slug."""

    @declared_attr
    def slug(cls):
        return Column(String(255), nullable=False, unique=True, index=True)


class OrderMixin:
    """Mixin for models that have an ordering field."""

    @declared_attr
    def order(cls):
        return Column(Integer, default=0, nullable=False, index=True)
