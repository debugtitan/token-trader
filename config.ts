import { PublicKey } from "@solana/web3.js"
import dotenv from "dotenv";

dotenv.config({
    path: ".env",
});
const Config = {
    AMM_ID: "ATDyH3UarK8wEbjwKwzFgzvNsw7UCC2uaTWFaEHZAxLW",
    WSOL: new PublicKey("So11111111111111111111111111111111111111112"),
    MINT: new PublicKey("8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR"),
    sellPercentage: Number(process.env.WALLET_HOLDINGS_BEFORE_SELL),
    randomTrade1: Number(process.env.RANDOM_TRADE_PERCENTAGE_START),
    randomTrade2: Number(process.env.RANDOM_TRADE_PERCENTAGE_END),
    TOKEN_SUPPLY: 1_000_000_000
}

export { Config }