from __future__ import absolute_import

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
KEYS_PATH = os.path.join(BASE_DIR, "keys.txt")
# Load our environment variables
load_dotenv(os.path.join(BASE_DIR, ".env"))

RPC_NODE = os.getenv("RPC")
LAMPORTS_PER_SOL = 1_000_000_000
RAYDIUM_LIQUIDITY_POOL = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_AUTHORITY = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
WSOL = "So11111111111111111111111111111111111111112"
TEST_TOKEN = "7zBbQAPGgoKvqcK74Yua8qGwEkEjAZxUPb5m3kKvvHyF"
TEST_AMM_KEY = "2SHSqG8NBuGJTgjErHmnpF9hp79eMG2jKfZUwheFrv62"


def read_private_keys():
    with open(KEYS_PATH, "r") as file:
        return [line.strip() for line in file.readlines()]
