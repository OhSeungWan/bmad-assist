"""Core module for bmad-assist configuration and utilities.

This module provides:
- Configuration models and singleton access via get_config()
- File-based configuration loading via load_global_config()
- Custom exception hierarchy with BmadAssistError as base
- Main loop orchestration via run_loop()
"""

from bmad_assist.core.config import (
    ENV_CREDENTIAL_KEYS,
    ENV_FILE_NAME,
    GLOBAL_CONFIG_PATH,
    MAX_CONFIG_SIZE,
    PROJECT_CONFIG_NAME,
    BmadPathsConfig,
    Config,
    MasterProviderConfig,
    MultiProviderConfig,
    PowerPromptConfig,
    ProviderConfig,
    _check_env_file_permissions,
    _mask_credential,
    get_config,
    load_config,
    load_config_with_project,
    load_env_file,
    load_global_config,
    reload_config,
)
from bmad_assist.core.config_editor import (
    ConfigEditor,
    ProvenanceTracker,
)
from bmad_assist.core.config_generator import (
    AVAILABLE_PROVIDERS,
    CONFIG_FILENAME,
    ConfigGenerator,
    run_config_wizard,
)
from bmad_assist.core.exceptions import (
    BmadAssistError,
    ConfigError,
    ProviderError,
    ProviderExitCodeError,
    ProviderTimeoutError,
)
from bmad_assist.core.loop import run_loop

__all__ = [
    # Config constants
    "ENV_CREDENTIAL_KEYS",
    "ENV_FILE_NAME",
    "GLOBAL_CONFIG_PATH",
    "MAX_CONFIG_SIZE",
    "PROJECT_CONFIG_NAME",
    # Config models
    "BmadPathsConfig",
    "Config",
    "MasterProviderConfig",
    "MultiProviderConfig",
    "PowerPromptConfig",
    "ProviderConfig",
    # Config functions
    "get_config",
    "load_config",
    "load_config_with_project",
    "load_env_file",
    "load_global_config",
    "reload_config",
    # Config editor
    "ConfigEditor",
    "ProvenanceTracker",
    # Config generator
    "AVAILABLE_PROVIDERS",
    "CONFIG_FILENAME",
    "ConfigGenerator",
    "run_config_wizard",
    # Credential helpers
    "_check_env_file_permissions",
    "_mask_credential",
    # Exceptions
    "BmadAssistError",
    "ConfigError",
    "ProviderError",
    "ProviderExitCodeError",
    "ProviderTimeoutError",
    # Loop orchestration
    "run_loop",
]
