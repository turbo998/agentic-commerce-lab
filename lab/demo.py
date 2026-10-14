"""Run the synthetic happy path and demonstrate a blocked cart substitution."""

import json
import logging
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.checkout import AuthorizationError, Checkout, CheckoutStore


def main() -> None:
    """Exercise an offline checkout without persistent personal data or secrets."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with TemporaryDirectory(prefix="commerce-lab-") as directory:
        store = CheckoutStore(Path(directory) / "checkout.sqlite3")
        quote = Checkout("synthetic-shop", "USD", "synthetic-headphones", 1, 7900)
        store.approve("approval-demo", quote, max_amount=8000, expires_at=200)
        receipt = store.execute("approval-demo", quote, request_key="request-demo", now=100)
        retry = CheckoutStore(store.path).execute(
            "approval-demo", quote, request_key="request-demo", now=201
        )
        logging.info(json.dumps({"receipt": asdict(receipt), "retry_same": retry == receipt}))
        try:
            store.execute(
                "approval-demo", replace(quote, amount=8100),
                request_key="different-request", now=100,
            )
        except AuthorizationError as error:
            logging.info(json.dumps({"blocked": str(error), "real_payments": False}))
        else:
            raise RuntimeError("Demo failed: unauthorized amount was accepted.")


if __name__ == "__main__":
    main()
