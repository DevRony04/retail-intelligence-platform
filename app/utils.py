import sys
from loguru import logger

def setup_logging():
    """
    Configures loguru to log to both stdout and a structured operational log file
    """
    # Remove default handler
    logger.remove()

    # Apply global patch to guarantee expected extra fields are present to prevent KeyErrors
    def patch_record(record):
        record["extra"].setdefault("trace_id", "SYSTEM")
        record["extra"].setdefault("store_id", "SYSTEM")
        record["extra"].setdefault("endpoint", "N/A")
        record["extra"].setdefault("latency_ms", 0)
        record["extra"].setdefault("event_count", 0)
        record["extra"].setdefault("status_code", 200)

    logger.configure(patcher=patch_record)

    # Formatter for structured logs
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[trace_id]}</cyan> | "
        "<magenta>{extra[store_id]}</magenta> | "
        "<yellow>{extra[endpoint]}</yellow> | "
        "Latency: <cyan>{extra[latency_ms]}ms</cyan> | "
        "Events: <yellow>{extra[event_count]}</yellow> | "
        "Status: <level>{extra[status_code]}</level> | "
        "{message}"
    )

    # Console Logging
    logger.add(
        sys.stdout,
        format=log_format,
        level="INFO",
        colorize=True
    )

    # Persistent File Logging for Production Auditing
    os_log_dir = "outputs/logs"
    import os
    os.makedirs(os_log_dir, exist_ok=True)
    logger.add(
        os.path.join(os_log_dir, "api.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[trace_id]} | {extra[store_id]} | {extra[endpoint]} | {extra[latency_ms]}ms | {extra[event_count]} | {extra[status_code]} | {message}",
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )

    print("Observability logs initialized successfully.")
