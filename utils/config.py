from __future__ import absolute_import

import os
from pathlib import Path
from dotenv import load_dotenv
from solders.pubkey import Pubkey  # type: ignore

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
KEYS_PATH = os.path.join(BASE_DIR, "keys.txt")
# Load our environment variables
load_dotenv(os.path.join(BASE_DIR, ".env"))

RPC_NODE = os.getenv("RPC")
""" RPC Node url"""

LAMPORTS_PER_SOL = 1_000_000_000  # canalso be 10**9
"""Number of decimals for WSOL"""

RAYDIUM_LIQUIDITY_POOL = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
"""Public Address of Raydium Liquidty Pool"""

RAYDIUM_AUTHORITY = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
"""Public Address of Raydium Authority"""

WSOL = "So11111111111111111111111111111111111111112"
""" Public Address of Solana Coin (WSOL)"""

TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
"""Public key that identifies the SPL token program."""

OPEN_BOOK_PROGRAM_ID = "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX"
""""Public address openbook market serum"""

TEST_TOKEN = "7zBbQAPGgoKvqcK74Yua8qGwEkEjAZxUPb5m3kKvvHyF"
"""Our Testing Token"""

TEST_AMM_KEY = "2SHSqG8NBuGJTgjErHmnpF9hp79eMG2jKfZUwheFrv62"
"""Test Token AMM ID"""


UNIT_PRICE = 10_000_000
UNIT_BUDGET = 100_000


def read_private_keys():
    with open(KEYS_PATH, "r") as file:
        return [line.strip() for line in file.readlines()]
