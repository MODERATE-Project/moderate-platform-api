import os

try:
    import coloredlogs

    log_level = os.getenv("LOG_LEVEL", "INFO")
    coloredlogs.install(level=log_level)
except Exception:
    pass
