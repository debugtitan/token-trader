from __future__ import absolute_import

import os
from pathlib import Path
from dotenv import load_dotenv
from solders.pubkey import Pubkey  # type: ignore

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
KEYS_PATH = os.path.join(BASE_DIR, "Wallets.txt")
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

RAYDIUM_CPMM = Pubkey.from_string("CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C")

RAYDIUM_CPMM_AUTHORITY = Pubkey.from_string("GpMZbSM2GgvTKHJirzeGfMFoaZ8UR2X7F4v8vHTvxFbL")

TEST_TOKEN = "8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR"
"""Our Testing Token"""

TEST_AMM_KEY = Pubkey.from_string("ATDyH3UarK8wEbjwKwzFgzvNsw7UCC2uaTWFaEHZAxLW")
"""Test Token AMM ID"""

BASE_VAULT = Pubkey.from_string("4PXRXECejNjuLc15oW8Wmx7baSVSwijA9nqLUJsgaPBy")
QUOTE_VAULT = Pubkey.from_string("2s1KoNYJPvbnW6TLZopxvXSyA1wak98uuV9iE2REM3Di")

UNIT_PRICE = 10_000_000
UNIT_BUDGET = 100_000
TOKEN_SUPPLY = 1_000_000_000


def read_private_keys():
    with open(KEYS_PATH, "r") as file:
        return [line.strip() for line in file.readlines()]
