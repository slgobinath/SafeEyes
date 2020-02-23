from abc import ABC, abstractmethod
from numbers import Integral


class IdleTimeInterface(ABC):
    """Tells how long the user has been idle."""
    # This could be a typing.Protocol in Python 3.8.

    @classmethod
    @abstractmethod
    def is_applicable(cls, context) -> bool:
        """Is this implementation usable in this context?"""
        pass

    @abstractmethod
    def idle_seconds(self) -> Integral:
        """Time since last user input, in seconds.

        Returns 0 on failure."""
        pass

    @abstractmethod
    def destroy(self) -> None:
        """Destroy this checker (clean up any resources)."""
        pass
