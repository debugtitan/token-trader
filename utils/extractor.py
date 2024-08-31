from io import BytesIO

from borsh_construct import CStruct, String, U8, U16, U64, Vec, Option, Bool, Enum

from construct import (
    Bytes,
    Int8ul,
    Int16ul,
    Int32ul,
    Int64ul,
    Padding,
    BitsInteger,
    BitsSwapped,
    BitStruct,
    Const,
    Flag,
    BytesInteger,
    Array,
    Struct,
)
from construct import Struct as cStruct

import base58, json

from solders.pubkey import Pubkey  # type: ignore


class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) is bytes:
            return o.decode("utf-8")
        return super(MyEncoder, self).default(o)


def remove_bytesio(obj):
    if isinstance(obj, dict):
        return {
            k: remove_bytesio(v) for k, v in obj.items() if not isinstance(v, BytesIO)
        }
    elif isinstance(obj, list):
        return [remove_bytesio(v) for v in obj if not isinstance(v, BytesIO)]
    else:
        return obj


def convert_bytes_to_pubkey(obj):
    if isinstance(obj, dict):
        return {k: convert_bytes_to_pubkey(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_pubkey(v) for v in obj]
    elif isinstance(obj, bytes):
        return str(Pubkey.from_bytes(obj))
    else:
        return obj


def getMetaData(data):
    decoded_info = base58.b58decode(data)
    # structure of the instruction
    instruction_structure = CStruct(
        "instructionDiscriminator" / U8,
        "createMetadataAccountArgsV3"
        / CStruct(
            "data"
            / CStruct(
                "name" / String,
                "symbol" / String,
                "uri" / String,
                "sellerFeeBasisPoints" / U16,
                "creators"
                / Option(
                    Vec(CStruct("address" / Bytes(32), "verified" / Bool, "share" / U8))
                ),
                "collection" / Option(CStruct("verified" / Bool, "key" / Bytes(32))),
                "uses"
                / Option(
                    CStruct(
                        "useMethod"
                        / Enum("Burn", "Multiple", "Single", enum_name="UseMethod"),
                        "remaining" / U64,
                        "total" / U64,
                    )
                ),
            ),
            "isMutable" / Bool,
            "collectionDetails"
            / Option(String),  # fixme: string is not correct, insert correct type
        ),
    )
    metadata = instruction_structure.parse(decoded_info)
    # for key, value in metadata.items():
    #     if isinstance(value, BytesIO):
    #         metadata[key] = base64.b64encode(value.read()).decode('utf-8')

    metadata = remove_bytesio(metadata)
    metadata = convert_bytes_to_pubkey(metadata)

    return json.dumps(metadata)


SWAP_LAYOUT = cStruct(
    "instruction" / Int8ul, "amount_in" / Int64ul, "min_amount_out" / Int64ul
)


AMM_INFO_LAYOUT_V4_1 = cStruct(
    "status" / Int64ul,
    "nonce" / Int64ul,
    "orderNum" / Int64ul,
    "depth" / Int64ul,
    "coinDecimals" / Int64ul,
    "pcDecimals" / Int64ul,
    "state" / Int64ul,
    "resetFlag" / Int64ul,
    "minSize" / Int64ul,
    "volMaxCutRatio" / Int64ul,
    "amountWaveRatio" / Int64ul,
    "coinLotSize" / Int64ul,
    "pcLotSize" / Int64ul,
    "minPriceMultiplier" / Int64ul,
    "maxPriceMultiplier" / Int64ul,
    "systemDecimalsValue" / Int64ul,
    #   // Fees
    "minSeparateNumerator" / Int64ul,
    "minSeparateDenominator" / Int64ul,
    "tradeFeeNumerator" / Int64ul,
    "tradeFeeDenominator" / Int64ul,
    "pnlNumerator" / Int64ul,
    "pnlDenominator" / Int64ul,
    "swapFeeNumerator" / Int64ul,
    "swapFeeDenominator" / Int64ul,
    #   // OutPutData
    "needTakePnlCoin" / Int64ul,
    "needTakePnlPc" / Int64ul,
    "totalPnlPc" / Int64ul,
    "totalPnlCoin" / Int64ul,
    "poolOpenTime" / Int64ul,
    "punishPcAmount" / Int64ul,
    "punishCoinAmount" / Int64ul,
    "orderbookToInitTime" / Int64ul,
    "swapCoinInAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapPcOutAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapCoin2PcFee" / Int64ul,
    "swapPcInAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapCoinOutAmount" / BytesInteger(16, signed=False, swapped=True),
    "swapPc2CoinFee" / Int64ul,
    "poolCoinTokenAccount" / Bytes(32),
    "poolPcTokenAccount" / Bytes(32),
    "coinMintAddress" / Bytes(32),
    "pcMintAddress" / Bytes(32),
    "lpMintAddress" / Bytes(32),
    "ammOpenOrders" / Bytes(32),
    "serumMarket" / Bytes(32),
    "serumProgramId" / Bytes(32),
    "ammTargetOrders" / Bytes(32),
    # "poolWithdrawQueue" / Bytes(32),
    # "poolTempLpTokenAccount" / Bytes(32),
    # "ammOwner" / Bytes(32),
    # "pnlOwner" / Bytes(32),
)


# We will use a bitstruct with 64 bits instead of the widebits implementation in serum-js.
ACCOUNT_FLAGS_LAYOUT = BitsSwapped(  # Swap to little endian
    BitStruct(
        "initialized" / Flag,
        "market" / Flag,
        "open_orders" / Flag,
        "request_queue" / Flag,
        "event_queue" / Flag,
        "bids" / Flag,
        "asks" / Flag,
        Const(0, BitsInteger(57)),  # Padding
    )
)

MARKET_LAYOUT = cStruct(
    Padding(5),
    # "account_flags" / ACCOUNT_FLAGS_LAYOUT,
    # "own_address" / Bytes(32),
    "vault_signer_nonce" / Int64ul,
    "base_mint" / Bytes(32),
    "quote_mint" / Bytes(32),
    "base_vault" / Bytes(32),
    # "base_deposits_total" / Int64ul,
    # "base_fees_accrued" / Int64ul,
    "quote_vault" / Bytes(32),
    # "quote_deposits_total" / Int64ul,
    # "quote_fees_accrued" / Int64ul,
    # "quote_dust_threshold" / Int64ul,
    # "request_queue" / Bytes(32),
    # "event_queue" / Bytes(32),
    # "bids" / Bytes(32),
    # "asks" / Bytes(32),
    # "base_lot_size" / Int64ul,
    # "quote_lot_size" / Int64ul,
    # "fee_rate_bps" / Int64ul,
    # "referrer_rebate_accrued" / Int64ul,
    Padding(7),
)

MINT_LAYOUT = cStruct(Padding(44), "decimals" / Int8ul, Padding(37))

PUBLIC_KEY_LAYOUT = Bytes(32)
POOL_INFO_LAYOUT = cStruct("instruction" / Int8ul, "simulate_type" / Int8ul)

LIQ_LAYOUT = cStruct("instruction" / Int8ul, "amount_in" / Int64ul)

SWAP_LAYOUT = Struct(
    # "instruction" / Int8ul,
    "amountInMax" / Int64ul,
    "amountOut" / Int64ul,
)
ACCOUNT_LAYOUT = cStruct(
    "mint" / PUBLIC_KEY_LAYOUT,
    "owner" / PUBLIC_KEY_LAYOUT,
    "amount" / Int64ul,
    "delegate_option" / Int32ul,
    "delegate" / PUBLIC_KEY_LAYOUT,
    "state" / Int8ul,
    "is_native_option" / Int32ul,
    "is_native" / Int64ul,
    "delegated_amount" / Int64ul,
    "close_authority_option" / Int32ul,
    "close_authority" / PUBLIC_KEY_LAYOUT,
)

CPMM_CONFIG_INFO_LAYOUT = cStruct(
    "blob_8" / Bytes(8),
    "bump" / Int8ul,
    "disableCreatePool" / Flag,
    "index" / Int16ul,
    "tradeFeeRate" / Int64ul,
    "protocolFeeRate" / Int64ul,
    "fundFeeRate" / Int64ul,
    "createPoolFee" / Int64ul,
    "protocolOwner" / PUBLIC_KEY_LAYOUT,
    "fundOwner" / PUBLIC_KEY_LAYOUT,
    "seq_u64_16" / Array(16, Int64ul),
)


CPMM_POOL_INFO_LAYOUT = Struct(
    "blob_8" / Bytes(8),
    "configId" / PUBLIC_KEY_LAYOUT,
    "poolCreator" / PUBLIC_KEY_LAYOUT,
    "vaultA" / PUBLIC_KEY_LAYOUT,
    "vaultB" / PUBLIC_KEY_LAYOUT,
    "mintLp" / PUBLIC_KEY_LAYOUT,
    "mintA" / PUBLIC_KEY_LAYOUT,
    "mintB" / PUBLIC_KEY_LAYOUT,
    "mintProgramA" / PUBLIC_KEY_LAYOUT,
    "mintProgramB" / PUBLIC_KEY_LAYOUT,
    "observationId" / PUBLIC_KEY_LAYOUT,
    "bump" / Int8ul,
    "status" / Int8ul,
    "lpDecimals" / Int8ul,
    "mintDecimalA" / Int8ul,
    "mintDecimalB" / Int8ul,
    "lpAmount" / Int64ul,
    "protocolFeesMintA" / Int64ul,
    "protocolFeesMintB" / Int64ul,
    "fundFeesMintA" / Int64ul,
    "fundFeesMintB" / Int64ul,
    "openTime" / Int64ul,
    "seq_u64_32" / Array(32, Int64ul),
)
