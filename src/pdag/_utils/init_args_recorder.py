from typing import Annotated, Any, Self

from typing_extensions import Doc


class InitArgsRecorder:
    """A mixin class that records the arguments used to initialize the instance.

    The arguments can be retrieved later using the `get_init_args` and `get_init_kwargs` methods.
    """

    # These are not class variables, but instance variables
    # They are declared here to inform type checkers.
    __init_args__: Annotated[tuple[Any, ...], Doc("Arguments used to initialize the instance.")]
    __init_kwargs__: Annotated[dict[str, Any], Doc("Keyword arguments used to initialize the instance.")]

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
