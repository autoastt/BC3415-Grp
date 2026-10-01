import os
import sys
import tempfile
from pathlib import Path

# Isolated, offline environment for every test run
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="scopeguard-test-")
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["ANTHROPIC_API_KEY"] = "test-not-used"
os.environ["ADMIN_TOKEN"] = "test-admin"
os.environ["RELEVANCE_THRESHOLD"] = "0.2"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
