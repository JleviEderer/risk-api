"""Hardcoded bytecode fixtures for testing.

These are representative samples — not the full bytecodes of real contracts.
They contain the key patterns our detectors look for.
"""

# Minimal clean contract: PUSH1 0x80 PUSH1 0x40 MSTORE + padding
# Should score SAFE (0) — no risky patterns, >200 bytes
CLEAN_CONTRACT = "6080604052" + "5b" * 200  # JUMPDEST padding

# Minimal ERC-20 dispatcher with standard selectors only
# transfer, balanceOf, totalSupply, approve, allowance, transferFrom
ERC20_DISPATCHER = (
    "6080604052"          # PUSH1 0x80 PUSH1 0x40 MSTORE
    "63a9059cbb"          # PUSH4 transfer
    "1461003457"          # EQ PUSH2 0x0034 JUMPI
    "6370a08231"          # PUSH4 balanceOf
    "1461005057"          # EQ PUSH2 0x0050 JUMPI
    "6318160ddd"          # PUSH4 totalSupply
    "1461006c57"          # EQ PUSH2 0x006c JUMPI
    "63095ea7b3"          # PUSH4 approve
    "1461008857"          # EQ PUSH2 0x0088 JUMPI
    "63dd62ed3e"          # PUSH4 allowance
    "146100a457"          # EQ PUSH2 0x00a4 JUMPI
    "6323b872dd"          # PUSH4 transferFrom
    "146100c057"          # EQ PUSH2 0x00c0 JUMPI
    + "00" * 200          # padding
)

# EIP-1967 proxy contract — PUSH32 <impl slot> + SLOAD + DELEGATECALL
# Should detect: proxy pattern (INFO) + delegatecall (INFO, downgraded)
PROXY_CONTRACT = (
    "7f"                  # PUSH32
    "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    "54"                  # SLOAD
    "f4"                  # DELEGATECALL
    + "00" * 200          # padding
)

# Honeypot pattern: has transfer selector + conditional REVERT
HONEYPOT_CONTRACT = (
    "63a9059cbb"          # PUSH4 transfer(address,uint256)
    "14"                  # EQ
    "57"                  # JUMPI
    "fd"                  # REVERT (blocks transfer)
    + "00" * 200          # padding
)

# Hidden mint + fee manipulation: malicious selectors
MALICIOUS_TOKEN = (
    "6340c10f19"          # PUSH4 mint(address,uint256)
    "1461003457"          # EQ PUSH2 JUMPI
    "6369fe0e2d"          # PUSH4 setFee(uint256)
    "1461005057"          # EQ PUSH2 JUMPI
    "63ec28438a"          # PUSH4 setMaxTxAmount(uint256)
    "1461006c57"          # EQ PUSH2 JUMPI
    + "00" * 200          # padding
)

# Contract with SELFDESTRUCT
SELFDESTRUCT_CONTRACT = (
    "6080604052"          # PUSH1 0x80 PUSH1 0x40 MSTORE
    "ff"                  # SELFDESTRUCT
    + "00" * 200          # padding
)

# Reentrancy pattern: CALL followed by SSTORE
REENTRANCY_CONTRACT = (
    "6080604052"          # PUSH1 0x80 PUSH1 0x40 MSTORE
    "f1"                  # CALL
    "55"                  # SSTORE
    + "00" * 200          # padding
)

# EOA — no bytecode
EOA = "0x"

# Tiny contract — less than 200 bytes, no proxy
TINY_CONTRACT = "6080604052" + "00" * 10
