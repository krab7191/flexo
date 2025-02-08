# src/database/base_adapter.py

from abc import ABC, abstractmethod


class DatabaseAdapter(ABC):
    """Abstract base class defining the interface for database operations.

    This class serves as a template for implementing database adapters,
    ensuring consistent interface across different database backends.
    All database implementations must inherit from this class and
    implement its abstract methods.

    Methods:
        add: Add data to the database
        search: Search for data in the database
        reset: Reset or clear the database

    Example:
        ```python
        class MyDatabaseClient(DatabaseAdapter):
            async def add(self, document, index_name):
                # Implementation for adding documents
                pass

            async def search(self, query, index_name):
                # Implementation for searching documents
                pass

            async def reset(self, index_name):
                # Implementation for resetting the database
                pass
        ```
    """

    @abstractmethod
    async def add(self, *args, **kwargs):
        """Add data to the database.

        This abstract method must be implemented by concrete database adapters
        to handle data insertion operations.

        Args:
            *args: Variable length argument list for flexibility across implementations
            **kwargs: Arbitrary keyword arguments for flexibility across implementations

        Raises:
            NotImplementedError: If the concrete class doesn't implement this method
        """
        pass

    @abstractmethod
    async def search(self, *args, **kwargs):
        """Search for data in the database.

        This abstract method must be implemented by concrete database adapters
        to handle search operations.

        Args:
            *args: Variable length argument list for flexibility across implementations
            **kwargs: Arbitrary keyword arguments for flexibility across implementations

        Raises:
            NotImplementedError: If the concrete class doesn't implement this method
        """
        pass

    @abstractmethod
    async def reset(self, *args, **kwargs):
        """Reset or clear data in the database.

        This abstract method must be implemented by concrete database adapters
        to handle database reset operations.

        Args:
            *args: Variable length argument list for flexibility across implementations
            **kwargs: Arbitrary keyword arguments for flexibility across implementations

        Raises:
            NotImplementedError: If the concrete class doesn't implement this method
        """
        pass
