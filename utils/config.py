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

def read_private_keys():
    with open(KEYS_PATH, "r") as file:
        return [line.strip() for line in file.readlines()]
