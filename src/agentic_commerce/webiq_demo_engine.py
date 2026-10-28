"""Microsoft Web IQ Agentic Commerce Demo Engine entry point (`src/agentic_commerce/webiq_demo_engine.py`).

Re-exports the production deterministic engine and CLI runner from `lab.webiq_commerce_demo`.
"""

from lab.webiq_commerce_demo import *  # noqa: F401,F403
from lab.webiq_commerce_demo import main

if __name__ == "__main__":
    main()

