from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    """
    Generic Abstract Base Class for all database repositories in the platform.
    Ensures consistent CRUD signatures and separates database execution details
    from domain business operations.
    """
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Inserts a new record into the database table.
        
        Args:
            entity: The domain entity object to insert.
            
        Returns:
            The created entity populated with auto-generated primary keys.
        """
        pass

    @abstractmethod
    def update(self, entity: T) -> None:
        """
        Updates an existing record matching the entity ID.
        
        Args:
            entity: The domain entity object to update.
        """
        pass

    @abstractmethod
    def delete(self, id_val: int) -> None:
        """
        Deletes a record matching the unique identifier.
        
        Args:
            id_val: The unique primary key ID.
        """
        pass

    @abstractmethod
    def find_by_id(self, id_val: int) -> Optional[T]:
        """
        Retrieves a record matching the unique identifier.
        
        Args:
            id_val: The unique primary key ID.
            
        Returns:
            The mapped domain entity object, or None if not found.
        """
        pass

    @abstractmethod
    def find_all(self) -> List[T]:
        """
        Retrieves all records from the table.
        
        Returns:
            A list of all mapped domain entity objects.
        """
        pass

    @abstractmethod
    def search(self, filters: Dict[str, Any]) -> List[T]:
        """
        Dynamically filters and searches records matching key-value properties.
        
        Args:
            filters: Dictionary representing column names and matching criteria values.
            
        Returns:
            A list of matching domain entity objects.
        """
        pass
