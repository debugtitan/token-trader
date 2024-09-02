import { Keypair, PublicKey, Connection } from "@solana/web3.js"
import { Raydium, TxVersion, CurveCalculator } from "@raydium-io/raydium-sdk-v2"
import bs58 from "bs58"
import { BN } from "bn.js";
import dotenv from "dotenv";

dotenv.config({
    path: ".env",
});


type TradeDirection = "BUY" | "SELL"

const trader = async (secretKey: string, tradeDirection: TradeDirection, amount: string) => {
    let swapResult;
    const MINT: PublicKey = new PublicKey("8Eewax7ooBdi5nwkp7VwittjEV9mVWAGhN1KVRJroeMR")
    const AMM_ID = "ATDyH3UarK8wEbjwKwzFgzvNsw7UCC2uaTWFaEHZAxLW"
    const WSOL: PublicKey = new PublicKey("So11111111111111111111111111111111111111112");
    const solanaConnection = new Connection(process.env.SOLANA_ENDPOINT ?? "https://api.mainnet-beta.solana.com");
    const buyAmount = new BN(amount);
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
        console.log("Pool datas ain't available")
        return
    }


    if (tradeDirection === "BUY") {
        swapResult = CurveCalculator.swapBaseOut({
            poolMintA: poolInfo.mintA,
            poolMintB: poolInfo.mintB,
            tradeFeeRate: rpcData?.configInfo!.tradeFeeRate,
            baseReserve: rpcData?.baseReserve,
            quoteReserve: rpcData?.quoteReserve,
            outputMint: MINT,
            outputAmount: buyAmount,
        })
    } else {
        swapResult = CurveCalculator.swapBaseOut({
            poolMintA: poolInfo.mintA,
            poolMintB: poolInfo.mintB,
            tradeFeeRate: rpcData?.configInfo!.tradeFeeRate,
            baseReserve: rpcData?.baseReserve,
            quoteReserve: rpcData?.quoteReserve,
            outputMint: WSOL,
            outputAmount: buyAmount,
        })

    }

    // ALWAYS NOTE ACTUAL AMOUNT MIGHT NOT BE SOLD "PRICE IMPACT, HIGH VOTALITY, LOW LIQUIDITY"
    try {
        const txn = await raydium.cpmm.swap({
            poolInfo,
            poolKeys,
            inputAmount: new BN(0), // if set fixedOut to true, this arguments won't be used
            fixedOut: true,
            swapResult: {
                sourceAmountSwapped: swapResult.amountIn,
                destinationAmountSwapped: buyAmount,
            },
            slippage: 0.001, // range: 1 ~ 0.0001, means 100% ~ 0.01% (know random slippage to use)
            baseIn: false,
            txVersion: TxVersion.V0,
            //optional: set up priority fee here
            computeBudgetConfig: {
                units: 600000,
                microLamports: 1000000,
            },
        })

        if (txn == null) {
            console.log("Couldn't process transaction")
            return
        }

        const { txId } = await txn.execute({ sendAndConfirm: true })
        console.log(`swapped: ${poolInfo.mintA.symbol} to ${poolInfo.mintB.symbol}:`, {
            txId: `https://solscan.io/tx/${txId}`,
        })
    } catch (e) {
        console.log("can't process transaction", e)
        process.exit(1)
    }
}



(async () => {
    //trader("64pFmk4d15akGxsCVpsCkhEQC3Ut2AxGLmyuHrk4vLbz1gNJxnifgYiQab7Bfgj1j7v2PFTMeAU756wkm7iCFz5q", "BUY", 0.01);
    trader("64pFmk4d15akGxsCVpsCkhEQC3Ut2AxGLmyuHrk4vLbz1gNJxnifgYiQab7Bfgj1j7v2PFTMeAU756wkm7iCFz5q", "SELL", "100000");
})();

