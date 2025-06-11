import logging
from rich.logging import RichHandler

# Configure colorful logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

# Export a reusable logger
log = logging.getLogger("setup")
