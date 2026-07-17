import asyncio
import time
import logging
import random

class AsyncDataLoader:
    def __init__(self):
        self._cache = {}  # Stores cached data: {endpoint: {"data": [...], "timestamp": float}}
        self._failed_jobs = []  # Stores endpoints that failed after retries
        self._semaphore = asyncio.Semaphore(3)  # Concurrency limit of 3 parallel requests
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _is_cache_valid(self, endpoint: str) -> bool:
        """
        Checks if the cached data for a given endpoint is valid (less than 60 seconds old).
        """
        if endpoint in self._cache:
            cached_entry = self._cache[endpoint]
            if "timestamp" in cached_entry and (time.time() - cached_entry["timestamp"]) < 60:
                return True
        return False

    async def _fetch_data_with_retries(self, endpoint: str):
        """
        Fetches data from a mock API endpoint with retries and exponential backoff.
        Uses a semaphore for concurrency control.
        """
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                async with self._semaphore:
                    logging.info(f"Fetching {endpoint} (Attempt {attempt + 1}/{MAX_RETRIES})")
                    # Simulate network call
                    # For demonstration, let's make some endpoints fail
                    if "fail" in endpoint and attempt < MAX_RETRIES - 1: # Make it fail for first few attempts
                        raise asyncio.TimeoutError(f"Simulated network timeout for {endpoint}")

                    await asyncio.sleep(random.uniform(0.5, 1.5)) # Simulate network latency

                    # Mock data generation
                    mock_data = [
                        {"id": 1, "amount": 100, "timestamp": time.time()},
                        {"id": 2, "amount": 5000, "timestamp": time.time() - 100}, # Old data
                        {"id": 3, "amount": 15000, "timestamp": time.time()},
                        {"id": 4, "amount": -20, "timestamp": time.time()}, # Invalid amount
                        {"id": 5, "amount": 200, "timestamp": None}, # Missing timestamp
                        {"id": 6, "amount": 10001, "timestamp": time.time()},
                        {"id": 7, "amount": 9999, "timestamp": time.time()},
                    ]
                    logging.info(f"Successfully fetched data for {endpoint}")
                    self._cache[endpoint] = {"data": mock_data, "timestamp": time.time()}
                    return mock_data
            except asyncio.TimeoutError as e:
                logging.warning(f"Network timeout for {endpoint}: {e}. Retrying...")
                if attempt < MAX_RETRIES - 1:
                    delay = 2 ** attempt
                    logging.info(f"Waiting for {delay} seconds before retrying {endpoint}...")
                    await asyncio.sleep(delay)
            except Exception as e:
                logging.error(f"An unexpected error occurred for {endpoint}: {e}. Retrying...")
                if attempt < MAX_RETRIES - 1:
                    delay = 2 ** attempt
                    logging.info(f"Waiting for {delay} seconds before retrying {endpoint}...")
                    await asyncio.sleep(delay)

        logging.error(f"Failed to fetch data for {endpoint} after {MAX_RETRIES} attempts.")
        self._failed_jobs.append(endpoint)
        return None

    def _process_data(self, data: list) -> list:
        """
        Processes a list of transaction dictionaries:
        - Filters out transactions with negative amount or missing timestamp.
        - Adds an 'is_high_risk' flag based on the transaction amount.
        """
        processed_transactions = []
        if not data:
            return processed_transactions

        for transaction in data:
            # Validate amount and timestamp
            if not isinstance(transaction, dict):
                logging.warning(f"Skipping non-dictionary transaction: {transaction}")
                continue

            amount = transaction.get("amount")
            timestamp = transaction.get("timestamp")

            if amount is None or not isinstance(amount, (int, float)) or amount < 0:
                logging.warning(f"Skipping transaction with invalid or negative amount: {transaction}")
                continue
            if timestamp is None:
                logging.warning(f"Skipping transaction with missing timestamp: {transaction}")
                continue

            # Add high-risk flag
            transaction["is_high_risk"] = amount > 10000
            processed_transactions.append(transaction)
        return processed_transactions

    async def fetch_and_process_transactions(self, endpoints: list) -> dict:
        """
        Fetches and processes transaction data from multiple endpoints concurrently.
        Uses caching, retries, and data validation.
        """
        all_processed_data = {}
        tasks = []

        async def _fetch_and_process_single_endpoint(endpoint):
            if self._is_cache_valid(endpoint):
                logging.info(f"Returning cached data for {endpoint}")
                # Return processed data from cache if it was stored processed,
                # otherwise process it again. For simplicity, we assume cache stores raw data.
                return self._process_data(self._cache[endpoint]["data"])
            else:
                fetched_data = await self._fetch_data_with_retries(endpoint)
                if fetched_data:
                    return self._process_data(fetched_data)
                return None

        for endpoint in endpoints:
            tasks.append(_fetch_and_process_single_endpoint(endpoint))

        results = await asyncio.gather(*tasks)

        for i, endpoint in enumerate(endpoints):
            if results[i] is not None:
                all_processed_data[endpoint] = results[i]
            else:
                all_processed_data[endpoint] = [] # Handle as per requirement for failed fetches

        return all_processed_data
