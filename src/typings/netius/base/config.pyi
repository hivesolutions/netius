"""
This type stub file was generated by pyright.
"""

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
FILE_NAME = ...
FILE_TEMPLATE = ...
HOME_FILE = ...
IMPORT_NAMES = ...
CASTS = ...
ENV_ENCODINGS = ...
CONFIGS = ...
CONFIG_F = ...
HOMES = ...
__builtins__ = ...
def conf(name, default=..., cast=..., ctx=...):
    """
    Retrieves the configuration value for the provided value
    defaulting to the provided default value in case no value
    is found for the provided name.

    An optional cast operation may be performed on the value
    in case it's requested.

    :type name: String
    :param name: The name of the configuration value to be
    retrieved.
    :type default: Object
    :param default: The default value to be retrieved in case
    no value was found for the provided name.
    :type cast: Type/String
    :param cast: The cast operation to be performed in the
    resolved value (optional).
    :type ctx: Dictionary
    :param ctx: The context dictionary to be used for situations
    where a more contextual configuration is meant to be used instead
    of the process wide global configuration.
    :rtype: Object
    :return: The value for the configuration with the requested
    name or the default value if no value was found.
    """
    ...

def conf_prefix(prefix, ctx=...): # -> dict[Any, Any]:
    ...

def conf_suffix(suffix, ctx=...): # -> dict[Any, Any]:
    ...

def conf_s(name, value, ctx=...): # -> None:
    ...

def conf_r(name, ctx=...): # -> None:
    ...

def conf_d(ctx=...): # -> dict[Any, Any]:
    ...

def conf_ctx(): # -> dict[str, dict[Any, Any]]:
    ...

def load(names=..., path=..., encoding=..., ctx=...): # -> None:
    ...

def load_file(name=..., path=..., encoding=..., ctx=...): # -> None:
    ...

def load_env(ctx=...): # -> None:
    ...

def get_homes(file_path=..., default=..., encoding=..., force_default=...): # -> list[Any] | list[str] | Literal['']:
    ...

