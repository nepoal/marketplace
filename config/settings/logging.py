import os

from config.env import env

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name} {module}.{funcName}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "marketplace_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(_BASE_DIR, "logs", "marketplace.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "marketplace_management": {
            "handlers": ["console", "marketplace_file"],
            "level": env("MARKETPLACE_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}
