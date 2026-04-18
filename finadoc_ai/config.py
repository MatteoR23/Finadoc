import os

INTERNAL_API_KEY: str = os.environ["INTERNAL_API_KEY"]

MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")
if not MISTRAL_API_KEY:
    raise RuntimeError("MISTRAL_API_KEY environment variable is not set or empty")

DATA_DIR: str = os.environ.get("DATA_DIR", "/data")
UPLOADS_DIR: str = os.path.join(DATA_DIR, "uploads")
OUTPUTS_DIR: str = os.path.join(DATA_DIR, "outputs")

MISTRAL_MODEL_SMALL = "mistral-small-latest"
MISTRAL_MODEL_LARGE = "mistral-large-latest"

PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")
