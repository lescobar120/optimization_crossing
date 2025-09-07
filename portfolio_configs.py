# portfolio_configs.py
from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml

@dataclass
class PortfolioConfig:
    benchmark: str
    min_trade_size: int
    round_lot_size: int
    min_trade_value: int
    # Optional overrides for specific portfolios
    sector_weight_tolerance: float = 0.01
    country_weight_tolerance: float = 0.01
    security_weight_tolerance: float = 0.01
    restricted_securities: List[str] = None
    no_trade_securities: List[str] = None
    cash_target: Optional[float] = None
    
    def __post_init__(self):
        if self.restricted_securities is None:
            self.restricted_securities = []
        if self.no_trade_securities is None:
            self.no_trade_securities = []

# Configuration with inheritance and defaults
PORTFOLIO_CONFIGS = {
    "S-17147": PortfolioConfig(
        benchmark="R1TPIT",
        min_trade_size=200,
        round_lot_size=200,
        min_trade_value=1000
    ),
    "P-93050": PortfolioConfig(
        benchmark="R200",
        min_trade_size=1000,
        round_lot_size=1000,
        min_trade_value=750000,
        #sector_weight_tolerance=0.02  # Custom override
    ),
    "P-61230": PortfolioConfig(
        benchmark="RTY",
        min_trade_size=100,
        round_lot_size=100,
        min_trade_value=100000,
        #restricted_securities=["TSLA", "GME"]  # Portfolio-specific restrictions
    ),
    "P-47227": PortfolioConfig(
        benchmark="RMC",
        min_trade_size=500,
        round_lot_size=500,
        min_trade_value=200000
    ),
    "P-36182": PortfolioConfig(
        benchmark="RUSLCLE",
        min_trade_size=200,
        round_lot_size=200,
        min_trade_value=100000
    )
}


class PortfolioConfigManager:
    def __init__(self, configs: Dict[str, PortfolioConfig]):
        self.configs = configs
    
    def get_config(self, portfolio_id: str) -> PortfolioConfig:
        """Get configuration for a specific portfolio."""
        if portfolio_id not in self.configs:
            raise ValueError(f"Portfolio {portfolio_id} not found in configs")
        return self.configs[portfolio_id]
    
    def get_all_portfolios(self) -> List[str]:
        """Get list of all portfolio IDs."""
        return list(self.configs.keys())
    
    def inject_restrictions(self, restrictions: Dict[str, Optional[List[str]]]):
        """
        Inject current restrictions into portfolio configs.
        
        Args:
            restrictions: Dictionary mapping portfolio_id -> list of restricted securities
                          None values are converted to empty lists
        """
        for portfolio_id, restricted_list in restrictions.items():
            if portfolio_id in self.configs:
                self.configs[portfolio_id].restricted_securities = restricted_list or []
    
    def add_global_restriction(self, security: str):
        """Add a security to restricted list for all portfolios"""
        for config in self.configs.values():
            if security not in config.restricted_securities:
                config.restricted_securities.append(security)