"""
Web3 Client for Polygon chain data.
Handles USDC balances and Conditional Token positions.
"""
from __future__ import annotations
from typing import Optional, Dict, List
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from app.core.config import settings


# ERC20 ABI (minimal for balance checking)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

# ERC1155 ABI (minimal for balance checking)
ERC1155_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_id", "type": "uint256"}
        ],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owners", "type": "address[]"},
            {"name": "_ids", "type": "uint256[]"}
        ],
        "name": "balanceOfBatch",
        "outputs": [{"name": "", "type": "uint256[]"}],
        "type": "function"
    }
]


class Web3Client:
    """
    Async Web3 client for Polygon blockchain interaction.
    Uses AsyncHTTPProvider for non-blocking calls.
    """
    
    def __init__(self):
        self._provider = AsyncHTTPProvider(settings.polygon_rpc_url)
        self._web3: Optional[AsyncWeb3] = None
        self._usdc_contract = None
        self._conditional_tokens_contract = None
    
    async def _get_web3(self) -> AsyncWeb3:
        """Get or create async Web3 instance."""
        if self._web3 is None:
            self._web3 = AsyncWeb3(self._provider)
        return self._web3
    
    async def _get_usdc_contract(self):
        """Get USDC contract instance."""
        if self._usdc_contract is None:
            web3 = await self._get_web3()
            self._usdc_contract = web3.eth.contract(
                address=web3.to_checksum_address(settings.usdc_contract_address),
                abi=ERC20_ABI
            )
        return self._usdc_contract
    
    async def _get_conditional_tokens_contract(self):
        """Get Conditional Tokens (ERC1155) contract instance."""
        if self._conditional_tokens_contract is None:
            web3 = await self._get_web3()
            self._conditional_tokens_contract = web3.eth.contract(
                address=web3.to_checksum_address(settings.conditional_tokens_address),
                abi=ERC1155_ABI
            )
        return self._conditional_tokens_contract
    
    async def get_usdc_balance(self, wallet_address: str) -> float:
        """
        Fetch USDC balance for a wallet.
        Returns balance in human-readable format (not wei).
        """
        try:
            web3 = await self._get_web3()
            contract = await self._get_usdc_contract()
            
            checksum_address = web3.to_checksum_address(wallet_address)
            
            # USDC has 6 decimals on Polygon
            balance_wei = await contract.functions.balanceOf(checksum_address).call()
            balance = balance_wei / 1_000_000  # 6 decimals
            
            return float(balance)
        except Exception as e:
            print(f"Error fetching USDC balance for {wallet_address}: {e}")
            return 0.0
    
    async def get_conditional_token_balance(
        self, 
        wallet_address: str, 
        token_id: int
    ) -> float:
        """
        Fetch balance of a specific conditional token.
        Returns balance in human-readable format.
        """
        try:
            web3 = await self._get_web3()
            contract = await self._get_conditional_tokens_contract()
            
            checksum_address = web3.to_checksum_address(wallet_address)
            
            balance_wei = await contract.functions.balanceOf(
                checksum_address, 
                token_id
            ).call()
            
            # Conditional tokens typically use 6 decimals (like USDC collateral)
            balance = balance_wei / 1_000_000
            
            return float(balance)
        except Exception as e:
            print(f"Error fetching token {token_id} balance: {e}")
            return 0.0
    
    async def get_conditional_token_balances_batch(
        self,
        wallet_address: str,
        token_ids: list[int]
    ) -> dict[int, float]:
        """
        Fetch multiple token balances in a single call.
        More efficient than individual calls.
        """
        if not token_ids:
            return {}
        
        try:
            web3 = await self._get_web3()
            contract = await self._get_conditional_tokens_contract()
            
            checksum_address = web3.to_checksum_address(wallet_address)
            
            # Create arrays for batch call
            owners = [checksum_address] * len(token_ids)
            
            balances_wei = await contract.functions.balanceOfBatch(
                owners,
                token_ids
            ).call()
            
            # Convert to dict with human-readable values
            result = {}
            for token_id, balance_wei in zip(token_ids, balances_wei):
                result[token_id] = balance_wei / 1_000_000
            
            return result
        except Exception as e:
            print(f"Error in batch balance fetch: {e}")
            # Fallback to individual calls
            result = {}
            for token_id in token_ids:
                result[token_id] = await self.get_conditional_token_balance(
                    wallet_address, 
                    token_id
                )
            return result
    
    async def is_connected(self) -> bool:
        """Check if Web3 connection is active."""
        try:
            web3 = await self._get_web3()
            return await web3.is_connected()
        except Exception:
            return False


# Global client instance
web3_client = Web3Client()
