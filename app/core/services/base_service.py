"""
Base service patterns for CRUD operations.
"""

import logging
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.models.base import BaseModel

# Type variables for generic service
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = logging.getLogger(__name__)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic base service class for CRUD operations.
    """

    def __init__(self, model: type[ModelType]):
        """
        Initialize the service with a model class.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    def get(self, db: Session, id: UUID | str) -> ModelType | None:
        """
        Get a single record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} with id {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    def get_or_404(self, db: Session, id: UUID | str) -> ModelType:
        """
        Get a single record by ID or raise 404 if not found.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Model instance

        Raises:
            HTTPException: 404 if record not found
        """
        obj = self.get(db, id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} not found"
            )
        return obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """
        Get multiple records with pagination and filtering.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters

        Returns:
            List of model instances
        """
        try:
            query = db.query(self.model)

            # Apply filters if provided
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Pydantic schema with creation data

        Returns:
            Created model instance
        """
        try:
            obj_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
            db_obj = self.model(**obj_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info(f"Created {self.model.__name__} with id {db_obj.id}")
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity error"
            )
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            db: Database session
            db_obj: Existing model instance
            obj_in: Pydantic schema or dict with update data

        Returns:
            Updated model instance
        """
        try:
            obj_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, 'dict') else obj_in

            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity error"
            )
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    def delete(self, db: Session, *, id: UUID | str) -> ModelType:
        """
        Delete a record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Deleted model instance
        """
        try:
            obj = self.get_or_404(db, id)
            db.delete(obj)
            db.commit()
            logger.info(f"Deleted {self.model.__name__} with id {id}")
            return obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )

    def count(self, db: Session, filters: dict[str, Any] | None = None) -> int:
        """
        Count records with optional filtering.

        Args:
            db: Database session
            filters: Dictionary of field filters

        Returns:
            Number of records
        """
        try:
            query = db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
