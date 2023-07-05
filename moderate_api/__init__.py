import os

try:
    import coloredlogs

    log_level = os.getenv("LOG_LEVEL", "DEBUG")
    coloredlogs.install(level=log_level)
except:
    pass
