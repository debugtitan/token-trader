import { Keypair, PublicKey, Connection } from "@solana/web3.js"
import { Raydium, TxVersion, CurveCalculator } from "@raydium-io/raydium-sdk-v2"
import bs58 from "bs58"
import BN from 'bn.js'
import dotenv from "dotenv";

dotenv.config({
    path: ".env",
});


type TradeDirection = "BUY" | "SELL"

const trader = async (secretKey: string, tradeDirection: TradeDirection, amount: number) => {
    let swapResult;
    let baseIn: boolean;
    const MINT = "8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR"
    const AMM_ID = "ATDyH3UarK8wEbjwKwzFgzvNsw7UCC2uaTWFaEHZAxLW"
    const WSOL: PublicKey = new PublicKey("So11111111111111111111111111111111111111112");
    const solanaConnection = new Connection(process.env.SOLANA_ENDPOINT ?? "https://api.mainnet-beta.solana.com");
    const buyAmount = new BN(amount * 10 ** 9);
    const wallet = Keypair.fromSecretKey(bs58.decode(secretKey));
    console.log(`🤖 Initiating bot for wallet: ${wallet.publicKey.toBase58()}.\n\n`)

    const raydium = await Raydium.load({
        connection: solanaConnection,
        owner: wallet,
        disableLoadToken: false
    });

    if (raydium == null) {
        console.log("Can't initialize swapper")
        return;
    }

    const data = await raydium.cpmm.getPoolInfoFromRpc(AMM_ID)
    if (data == null) {
        console.log("Can't get pool info")
        return
    }
    const poolInfo = data.poolInfo
    const poolKeys = data.poolKeys
    const rpcData = data.rpcData

    if (poolInfo == null || rpcData == null) {
        console.log("Pool data's ain't available")
        return
    }

    console.log("Checking Trade Direction ♿")

    if (tradeDirection === "BUY") {
        baseIn = true
        swapResult = CurveCalculator.swap(
            buyAmount,
            baseIn ? rpcData.baseReserve : rpcData.quoteReserve,
            baseIn ? rpcData.quoteReserve : rpcData.baseReserve,
            rpcData.configInfo!.tradeFeeRate
        )


    } else {
        baseIn = false
        swapResult = CurveCalculator.swap(
            buyAmount,
            baseIn ? rpcData.baseReserve : rpcData.quoteReserve,
            baseIn ? rpcData.quoteReserve : rpcData.baseReserve,
            rpcData.configInfo!.tradeFeeRate
        )
    }

    
    const { execute } = await raydium.cpmm.swap({
        poolInfo,
        poolKeys,
        inputAmount: buyAmount,
        swapResult,
        slippage: 0.001, // range: 1 ~ 0.0001, means 100% ~ 0.01%
        baseIn,
        // optional: set up priority fee here
        computeBudgetConfig: {
            units: 600000,
            microLamports: 10000000,
        },
    })

    // don't want to wait confirm, set sendAndConfirm to false or don't pass any params to execute
    const { txId } = await execute({ sendAndConfirm: true })
    console.log(`swapped: txId: https://solscan.io/tx/${txId}`)
}



(async () => {
    trader("64pFmk4d15akGxsCVpsCkhEQC3Ut2AxGLmyuHrk4vLbz1gNJxnifgYiQab7Bfgj1j7v2PFTMeAU756wkm7iCFz5q", "BUY", 0.03);
    //trader("64pFmk4d15akGxsCVpsCkhEQC3Ut2AxGLmyuHrk4vLbz1gNJxnifgYiQab7Bfgj1j7v2PFTMeAU756wkm7iCFz5q", "SELL", 1_000_000);
})();

