"""Function selector extraction and malicious/suspicious selector databases.

Selector values are the first 4 bytes of keccak256(signature).
All values hardcoded to avoid keccak256 dependency.
"""

from __future__ import annotations

from risk_api.analysis.disassembler import Instruction

FEE_MANIPULATION_LABEL_TERMS = (
    "fee",
    "tax",
    "maxbuy",
    "maxtx",
    "maxtxn",
    "maxtransfer",
    "maxwallet",
    "maxhold",
    "txlimit",
    "maxsell",
    "walletlimit",
)

# Malicious selectors — presence is a strong negative signal
MALICIOUS_SELECTORS: dict[bytes, str] = {
    # mint(address,uint256) — hidden mint capability
    bytes.fromhex("40c10f19"): "mint(address,uint256)",
    # mint(uint256) — unconstrained mint
    bytes.fromhex("a0712d68"): "mint(uint256)",
    # blacklist(address)
    bytes.fromhex("44337ea1"): "blacklist(address)",
    # addToBlacklist(address)
    bytes.fromhex("44d75fa5"): "addToBlacklist(address)",
    # setFee(uint256) — fee manipulation
    bytes.fromhex("69fe0e2d"): "setFee(uint256)",
    # setTaxFee(uint256)
    bytes.fromhex("c0b0fda2"): "setTaxFee(uint256)",
    # setMaxTxAmount(uint256) — transaction limit manipulation
    bytes.fromhex("ec28438a"): "setMaxTxAmount(uint256)",
    # setMaxWalletSize(uint256)
    bytes.fromhex("b6c52324"): "setMaxWalletSize(uint256)",
    # setMaxBuyAmount(uint256)
    bytes.fromhex("f34eb0b8"): "setMaxBuyAmount(uint256)",
    # setTxLimit(uint256)
    bytes.fromhex("5c85974f"): "setTxLimit(uint256)",
    # setMaxTxnAmount(uint256)
    bytes.fromhex("74010ece"): "setMaxTxnAmount(uint256)",
    # setMaxSellAmount(uint256)
    bytes.fromhex("e99c9d09"): "setMaxSellAmount(uint256)",
    # setWalletLimit(uint256)
    bytes.fromhex("f1d5f517"): "setWalletLimit(uint256)",
    # setMaxWalletAmount(uint256)
    bytes.fromhex("27a14fc2"): "setMaxWalletAmount(uint256)",
    # setMaxHoldAmount(uint256)
    bytes.fromhex("d8b60040"): "setMaxHoldAmount(uint256)",
    # setMaxTransferAmount(uint256)
    bytes.fromhex("8bf55409"): "setMaxTransferAmount(uint256)",
}

# Suspicious selectors — risky but context-dependent
SUSPICIOUS_SELECTORS: dict[bytes, str] = {
    # setApprovalForAll(address,bool) — could enable rug pull
    bytes.fromhex("a22cb465"): "setApprovalForAll(address,bool)",
    # renounceOwnership() — sometimes good (locked), sometimes bait
    bytes.fromhex("715018a6"): "renounceOwnership()",
    # transferOwnership(address)
    bytes.fromhex("f2fde38b"): "transferOwnership(address)",
    # withdraw() — admin withdrawal
    bytes.fromhex("3ccfd60b"): "withdraw()",
    # setSwapEnabled(bool) — can disable trading
    bytes.fromhex("e01af92c"): "setSwapEnabled(bool)",
    # setTradingEnabled(bool) — can gate when trading is allowed
    bytes.fromhex("c2e5ec04"): "setTradingEnabled(bool)",
    # enableTrading() — can flip trading on at owner discretion
    bytes.fromhex("8a8c523c"): "enableTrading()",
    # excludeFromFee(address) — selective fee bypass
    bytes.fromhex("437823ec"): "excludeFromFee(address)",
    # excludeFromFees(address,bool) — selective fee bypass with explicit toggle
    bytes.fromhex("c0246668"): "excludeFromFees(address,bool)",
    # setIsExcludedFromFee(address,bool) — explicit fee-exemption toggle
    bytes.fromhex("f3d7a2f8"): "setIsExcludedFromFee(address,bool)",
    # pause() — common enough to warn on, but not to hard-block by itself
    bytes.fromhex("8456cb59"): "pause()",
}

# Standard ERC-20 selectors (for reference / false-positive filtering)
ERC20_SELECTORS: dict[bytes, str] = {
    bytes.fromhex("18160ddd"): "totalSupply()",
    bytes.fromhex("70a08231"): "balanceOf(address)",
    bytes.fromhex("a9059cbb"): "transfer(address,uint256)",
    bytes.fromhex("dd62ed3e"): "allowance(address,address)",
    bytes.fromhex("095ea7b3"): "approve(address,uint256)",
    bytes.fromhex("23b872dd"): "transferFrom(address,address,uint256)",
}


def extract_selectors(instructions: list[Instruction]) -> set[bytes]:
    """Extract 4-byte function selectors from disassembled bytecode.

    Looks for PUSH4 instructions, which typically appear in the function
    dispatcher (the big if/else chain at contract entry).
    """
    selectors: set[bytes] = set()
    for instr in instructions:
        if instr.name == "PUSH4" and len(instr.operand) == 4:
            selectors.add(instr.operand)
    return selectors


def find_malicious_selectors(
    selectors: set[bytes],
) -> dict[bytes, str]:
    """Return malicious selectors found in the given set."""
    return {s: MALICIOUS_SELECTORS[s] for s in selectors if s in MALICIOUS_SELECTORS}


def find_suspicious_selectors(
    selectors: set[bytes],
) -> dict[bytes, str]:
    """Return suspicious selectors found in the given set."""
    return {
        s: SUSPICIOUS_SELECTORS[s] for s in selectors if s in SUSPICIOUS_SELECTORS
    }


def is_fee_manipulation_label(label: str) -> bool:
    """Return whether a selector label maps to the fee/limit manipulation family."""
    lowered = label.lower()
    return any(term in lowered for term in FEE_MANIPULATION_LABEL_TERMS)
