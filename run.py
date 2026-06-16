import logging
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.scheduler import init_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = create_app()

if os.environ.get("ENABLE_SCHEDULER", "true").lower() == "true":
    init_scheduler(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
