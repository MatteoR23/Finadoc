import os

INTERNAL_API_KEY: str = os.environ.get("INTERNAL_API_KEY", "")
if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY environment variable is not set or empty")

MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")
if not MISTRAL_API_KEY:
    raise RuntimeError("MISTRAL_API_KEY environment variable is not set or empty")

DATA_DIR: str = os.environ.get("DATA_DIR", "/data")
UPLOADS_DIR: str = os.path.join(DATA_DIR, "uploads")
OUTPUTS_DIR: str = os.path.join(DATA_DIR, "outputs")

MISTRAL_MODEL_SMALL = "mistral-small-latest"
MISTRAL_MODEL_LARGE = "mistral-large-latest"

PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")

# S3 / MinIO
S3_ENDPOINT_URL: str = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY: str = os.environ.get("S3_ACCESS_KEY", "finlens")
S3_SECRET_KEY: str = os.environ.get("S3_SECRET_KEY", "finlens_secret")
S3_DOCUMENTS_BUCKET: str = os.environ.get("S3_DOCUMENTS_BUCKET", "finlens-documents")
S3_OUTPUTS_BUCKET: str = os.environ.get("S3_OUTPUTS_BUCKET", "finlens-outputs")
