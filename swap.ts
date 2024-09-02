import bs58 from "bs58"
import BN from "bn.js"
import * as fs from 'fs';
import { Connection, Keypair, PublicKey } from "@solana/web3.js"
import { getAssociatedTokenAddressSync } from "@solana/spl-token"
import { Raydium, TxVersion, CurveCalculator } from "@raydium-io/raydium-sdk-v2"
import dotenv from "dotenv";

dotenv.config({
    path: ".env",
});

function getRandomWallet(filePath: string = "Wallets.txt"): string {
    const data = fs.readFileSync(filePath, 'utf-8');
    const keys = data.split(/\r?\n/).filter(key => key.trim() !== '');
    const randomIndex = Math.floor(Math.random() * keys.length);
    return keys[randomIndex];
}

function getSellAmount(walletHolding: number | null): number | 0 {
    if (walletHolding === null) {
        return 0;
    }
    const percentageToSell = Math.random() * (10 - 2) + 2; // random 2-10%
    const sellAmount = (percentageToSell / 100) * walletHolding;
    return sellAmount;
}


class RaySwap {
    private solanaConnection: Connection;
    private wallet: Keypair;
    private raydium: Raydium | null = null;
    private MINT: PublicKey = new PublicKey("8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR")
    private AMM_ID = "ATDyH3UarK8wEbjwKwzFgzvNsw7UCC2uaTWFaEHZAxLW"
    private WSOL: PublicKey = new PublicKey("So11111111111111111111111111111111111111112");
    allPoolKeysJson: any[] = [];

    constructor(secretKey: string) {
        this.solanaConnection = new Connection(process.env.SOLANA_ENDPOINT ?? "https://api.mainnet-beta.solana.com");
        this.wallet = Keypair.fromSecretKey(bs58.decode(secretKey));

    }

    /**
     * Initializes the Raydium instance by loading necessary data.
     * 
     * @returns {Promise<void>} A promise that resolves once the Raydium instance is successfully loaded.
     */
    async init() {
        console.log(`🤖 Initiating bot for wallet: ${this.wallet.publicKey.toBase58()}.\n\n`)
        return this.raydium = await Raydium.load({
            connection: this.solanaConnection,
            owner: this.wallet,
            disableLoadToken: false
        });

    }

    /**get wallet token balance */
    async getTokenBalance() {
        const associateTokenAccount = getAssociatedTokenAddressSync(this.MINT, this.wallet.publicKey);
        return (await this.solanaConnection.getTokenAccountBalance(associateTokenAccount)).value.uiAmount
    }

    /** get wallet solana balance */
    async getBalance() {
        return await this.solanaConnection.getBalance(this.wallet.publicKey)
    }

    async main() {
        const solBalance = await this.getBalance()
        const tokenBalance = await this.getTokenBalance()
        const sellAmount = getSellAmount(tokenBalance)
        console.log(`Wallet: ${this.wallet.publicKey}\nSOL: ${solBalance}\nTAKY: ${tokenBalance}\nSell Amount: ${sellAmount}`)


        const outputAmount = new BN(sellAmount * 10 ** 9)//
        const data = await this.raydium?.cpmm.getPoolInfoFromRpc(this.AMM_ID)
        if (data == null) {
            return
        }
        const poolInfo = data.poolInfo
        const poolKeys = data.poolKeys
        const rpcData = data.rpcData

        if (poolInfo == null || rpcData == null) {
            return
        }
        const baseIn = this.MINT.toString() === poolInfo.mintA.address
        const swapResult = CurveCalculator.swap(
            outputAmount,
            baseIn ? rpcData.baseReserve : rpcData.quoteReserve,
            baseIn ? rpcData.quoteReserve : rpcData.baseReserve,
            rpcData.configInfo!.tradeFeeRate
        )

        // ALWAYS NOTE ACTUAL AMOUNT MIGHT NOT BE SOLD "PRICE IMPACT, HIGH VOTALITY, LOW LIQUIDITY"
        const txn = await this.raydium?.cpmm.swap({
            poolInfo,
            poolKeys,
            inputAmount: outputAmount,
            swapResult,
            slippage: 0.001, // range: 1 ~ 0.0001, means 100% ~ 0.01%
            baseIn,
            // optional: set up priority fee here
            computeBudgetConfig: {
                units: 600000,
                microLamports: 10000000,
            },
        })

        if (txn == null) {
            return
        }
        try {
            const { txId } = await txn.execute({ sendAndConfirm: true })
            console.log(`swapped: ${poolInfo.mintA.symbol} to ${poolInfo.mintB.symbol}:`, {
                txId: `https://solscan.io/tx/${txId}`,
            })
            return
        } catch (e) {
            console.log(e)
            process.exit()
        }
    }

}




(async () => {
    const wallet = getRandomWallet();
    const raySwap = new RaySwap(wallet);
    await raySwap.init();
    await raySwap.main()
})();

