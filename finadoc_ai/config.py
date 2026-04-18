import os

MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")

MISTRAL_MODEL_SMALL = "mistral-small-latest"
MISTRAL_MODEL_LARGE = "mistral-large-latest"

PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")

# S3 / MinIO
S3_ENDPOINT_URL: str = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY: str = os.environ.get("S3_ACCESS_KEY", "finadoc")
S3_SECRET_KEY: str = os.environ.get("S3_SECRET_KEY", "finadoc_secret")
S3_DOCUMENTS_BUCKET: str = os.environ.get("S3_DOCUMENTS_BUCKET", "finadoc-documents")
S3_OUTPUTS_BUCKET: str = os.environ.get("S3_OUTPUTS_BUCKET", "finadoc-outputs")
