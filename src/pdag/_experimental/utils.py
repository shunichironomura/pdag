from typing import Any, Self


class InitArgsRecorder:
    # These are not class variables, but instance variables
    # They are declared here to inform type checkers.
    __init_args__: tuple[Any, ...]
    __init_kwargs__: dict[str, Any]

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        # Create the instance first
        instance = super().__new__(cls)
        # Save the arguments for later inspection
        instance.__init_args__ = args
        instance.__init_kwargs__ = kwargs
        return instance
