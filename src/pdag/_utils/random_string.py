import random
import string


def generate_random_string(length: int = 6) -> str:
    # Return random string
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311
