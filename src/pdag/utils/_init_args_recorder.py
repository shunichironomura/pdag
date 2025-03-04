from typing import Any, Self


class InitArgsRecorder:
    """A mixin class that records the arguments used to initialize the instance."""

    # These are not class variables, but instance variables
    # They are declared here to inform type checkers.
    __init_args__: tuple[Any, ...]
    __init_kwargs__: dict[str, Any]

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Record the arguments used to initialize the instance."""
        # Create the instance first
        instance = super().__new__(cls)
        # Save the arguments for later inspection
        # This is a bit of a hack to avoid assigning to attributes
        # even if the inherited dataclass has frozen=True
        object.__setattr__(instance, "__init_args__", args)
        object.__setattr__(instance, "__init_kwargs__", kwargs)
        return instance

    def get_init_args(self) -> tuple[Any, ...]:
        """Return the arguments used to initialize the instance."""
        return self.__init_args__

    def get_init_kwargs(self) -> dict[str, Any]:
        """Return the keyword arguments used to initialize the instance."""
        return self.__init_kwargs__
