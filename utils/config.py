from __future__ import absolute_import

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Load our environment variables
load_dotenv(os.path.join(BASE_DIR,".env"))

RPC_NODE = os.getenv("RPC")