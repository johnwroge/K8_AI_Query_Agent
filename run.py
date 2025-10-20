
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import create_app
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = create_app()
    print("Starting Kubernetes AI Debug Assistant on port 8000")
    app.run(host="0.0.0.0", port=8000, debug=False)


