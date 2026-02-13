"""
SQLite Database Service for persistent storage.
Handles wallets, settings, and user preferences.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

from app.core.config import settings


@dataclass
class WalletRecord:
    """Wallet database record."""
    address: str
    name: Optional[str] = None
    is_active: bool = True


@dataclass
class UserSettings:
    """User settings record."""
    user_id: str = "default"
    kelly_multiplier: float = 0.25
    max_risk_cap: float = 0.05
    min_wallets: int = 2
    hide_lottery: bool = False
    connected_wallet: Optional[str] = None
    longshot_tolerance: float = 1.0
    trend_mode: bool = True
    # Whale Quality & De-Biased Kelly settings
    # Yield Mode Settings
    yield_trigger_price: float = 0.85
    yield_fixed_pct: float = 0.10
    yield_min_whales: int = 3


class DatabaseService:
    """SQLite database service for persistent storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(settings.wallets_file_path).parent / "polybot.db")
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Wallets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT UNIQUE NOT NULL,
                    name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY DEFAULT 'default',
                    kelly_multiplier REAL DEFAULT 0.25,
                    max_risk_cap REAL DEFAULT 0.05,
                    min_wallets INTEGER DEFAULT 2,
                    hide_lottery BOOLEAN DEFAULT 0,
                    connected_wallet TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Wallet names (labels) table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_names (
                    address TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Price history table for momentum scoring
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_market 
                ON price_history(market_id, recorded_at)
            """)
            
            # Insert default settings if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO user_settings (user_id) VALUES ('default')
            """)
            
            # Migrate: add new columns if missing
            for col_sql in [
                "ALTER TABLE user_settings ADD COLUMN longshot_tolerance REAL DEFAULT 1.0",
                "ALTER TABLE user_settings ADD COLUMN trend_mode BOOLEAN DEFAULT 1",
                "ALTER TABLE user_settings ADD COLUMN flb_correction_mode TEXT DEFAULT 'STANDARD'",
                "ALTER TABLE user_settings ADD COLUMN optimism_tax BOOLEAN DEFAULT 1",
                "ALTER TABLE user_settings ADD COLUMN min_whale_tier TEXT DEFAULT 'ALL'",
                "ALTER TABLE user_settings ADD COLUMN ignore_bagholders BOOLEAN DEFAULT 1",
                "ALTER TABLE user_settings ADD COLUMN yield_trigger_price REAL DEFAULT 0.85",
                "ALTER TABLE user_settings ADD COLUMN yield_fixed_pct REAL DEFAULT 0.10",
                "ALTER TABLE user_settings ADD COLUMN yield_min_whales INTEGER DEFAULT 3",
            ]:
                try:
                    cursor.execute(col_sql)
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
                except sqlite3.OperationalError:
                    pass

            # Ensure whale_scores table exists first
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whale_scores (
                    address TEXT PRIMARY KEY,
                    total_score INTEGER DEFAULT 50,
                    roi_score INTEGER DEFAULT 50,
                    discipline_score INTEGER DEFAULT 50,
                    precision_score INTEGER DEFAULT 50,
                    timing_score INTEGER DEFAULT 50,
                    tier TEXT DEFAULT 'UNRATED',
                    tags TEXT DEFAULT '[]',
                    trade_count INTEGER DEFAULT 0,
                    details TEXT DEFAULT '{}',
                    win_rate REAL DEFAULT 0.0,
                    roi_perf REAL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migrate: add whale stats columns to existing table if needed
            for col_sql in [
                "ALTER TABLE whale_scores ADD COLUMN win_rate REAL DEFAULT 0.0",
                "ALTER TABLE whale_scores ADD COLUMN roi_perf REAL DEFAULT 0.0",
            ]:
                try:
                    cursor.execute(col_sql)
                except sqlite3.OperationalError:
                    pass
            
            # Whale scores table

    
    # =========================================================================
    # Wallet Operations
    # =========================================================================
    
    def get_wallets(self, active_only: bool = True) -> List[WalletRecord]:
        """Get all tracked wallets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT address, name, is_active FROM wallets WHERE is_active = 1")
            else:
                cursor.execute("SELECT address, name, is_active FROM wallets")
            
            return [
                WalletRecord(
                    address=row["address"],
                    name=row["name"],
                    is_active=bool(row["is_active"])
                )
                for row in cursor.fetchall()
            ]
    
    def add_wallet(self, address: str, name: Optional[str] = None) -> bool:
        """Add a wallet to tracking."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO wallets (address, name, is_active) VALUES (?, ?, 1)",
                    (address.lower(), name)
                )
                return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet from tracking (soft delete)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE wallets SET is_active = 0 WHERE LOWER(address) = LOWER(?)",
                (address,)
            )
            return cursor.rowcount > 0
    
    def update_wallet_name(self, address: str, name: str) -> bool:
        """Update wallet display name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE wallets SET name = ? WHERE LOWER(address) = LOWER(?)",
                (name, address)
            )
            return cursor.rowcount > 0
    
    # =========================================================================
    # Settings Operations  
    # =========================================================================
    
    def get_settings(self, user_id: str = "default") -> UserSettings:
        """Get user settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserSettings(
                    user_id=row["user_id"],
                    kelly_multiplier=row["kelly_multiplier"],
                    max_risk_cap=row["max_risk_cap"],
                    min_wallets=row["min_wallets"],
                    hide_lottery=bool(row["hide_lottery"]),
                    connected_wallet=row["connected_wallet"],
                    longshot_tolerance=row["longshot_tolerance"] if "longshot_tolerance" in row.keys() else 1.0,
                    trend_mode=bool(row["trend_mode"]) if "trend_mode" in row.keys() else True,
                    yield_trigger_price=row["yield_trigger_price"] if "yield_trigger_price" in row.keys() else 0.85,
                    yield_fixed_pct=row["yield_fixed_pct"] if "yield_fixed_pct" in row.keys() else 0.10,
                    yield_min_whales=row["yield_min_whales"] if "yield_min_whales" in row.keys() else 3,
                )
            
            return UserSettings(user_id=user_id)
    
    def update_settings(
        self,
        user_id: str = "default",
        kelly_multiplier: Optional[float] = None,
        max_risk_cap: Optional[float] = None,
        min_wallets: Optional[int] = None,
        hide_lottery: Optional[bool] = None,
        connected_wallet: Optional[str] = None,
        longshot_tolerance: Optional[float] = None,
        trend_mode: Optional[bool] = None,
        yield_trigger_price: Optional[float] = None,
        yield_fixed_pct: Optional[float] = None,
        yield_min_whales: Optional[int] = None,
    ) -> UserSettings:
        """Update user settings."""
        current = self.get_settings(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_settings 
                (user_id, kelly_multiplier, max_risk_cap, min_wallets, hide_lottery, 
                 connected_wallet, longshot_tolerance, trend_mode,
                 yield_trigger_price, yield_fixed_pct, yield_min_whales,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                kelly_multiplier if kelly_multiplier is not None else current.kelly_multiplier,
                max_risk_cap if max_risk_cap is not None else current.max_risk_cap,
                min_wallets if min_wallets is not None else current.min_wallets,
                hide_lottery if hide_lottery is not None else current.hide_lottery,
                connected_wallet if connected_wallet is not None else current.connected_wallet,
                longshot_tolerance if longshot_tolerance is not None else current.longshot_tolerance,
                trend_mode if trend_mode is not None else current.trend_mode,
                yield_trigger_price if yield_trigger_price is not None else current.yield_trigger_price,
                yield_fixed_pct if yield_fixed_pct is not None else current.yield_fixed_pct,
                yield_min_whales if yield_min_whales is not None else current.yield_min_whales,
            ))
        
        return self.get_settings(user_id)
    
    # =========================================================================
    # Wallet Names (Labels)
    # =========================================================================
    
    def get_wallet_names(self) -> Dict[str, str]:
        """Get all wallet name labels."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT address, name FROM wallet_names")
            return {row["address"]: row["name"] for row in cursor.fetchall()}
    
    def set_wallet_name(self, address: str, name: str) -> bool:
        """Set a wallet name label."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO wallet_names (address, name) VALUES (?, ?)",
                (address.lower(), name)
            )
            return True
    
    # =========================================================================
    # Migration Helper
    # =========================================================================
    
    def migrate_from_json(self, json_path: str) -> int:
        """Migrate wallets from JSON file to database."""
        import json
        
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                wallets = data.get("wallets", [])
                
                count = 0
                for wallet in wallets:
                    if self.add_wallet(wallet):
                        count += 1
                
                return count
        except (FileNotFoundError, json.JSONDecodeError):
            return 0
    
    # =========================================================================
    # Price History (for Momentum Scoring)
    # =========================================================================
    
    def record_price(self, market_id: str, price: float) -> None:
        """Record a market price snapshot."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO price_history (market_id, price) VALUES (?, ?)",
                (market_id, price)
            )
    
    def record_prices_batch(self, prices: List[tuple]) -> None:
        """Record multiple price snapshots. prices = [(market_id, price), ...]"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO price_history (market_id, price) VALUES (?, ?)",
                prices
            )
    
    def get_7d_average(self, market_id: str) -> Optional[float]:
        """Get the 7-day average price for a market."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(price) as avg_price
                FROM price_history
                WHERE market_id = ? 
                AND recorded_at >= datetime('now', '-7 days')
            """, (market_id,))
            row = cursor.fetchone()
            if row and row["avg_price"] is not None:
                return float(row["avg_price"])
            return None
    
    def get_7d_averages_batch(self) -> Dict[str, float]:
        """Get 7-day averages for all tracked markets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT market_id, AVG(price) as avg_price
                FROM price_history
                WHERE recorded_at >= datetime('now', '-7 days')
                GROUP BY market_id
            """)
            return {
                row["market_id"]: float(row["avg_price"])
                for row in cursor.fetchall()
            }
    
    def prune_old_prices(self, days: int = 14) -> int:
        """Remove price history older than N days."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM price_history WHERE recorded_at < datetime('now', ? || ' days')",
                (f"-{days}",)
            )
            return cursor.rowcount
    
    # =========================================================================
    # Whale Scores
    # =========================================================================
    
    def save_whale_score(self, address: str, score_data: dict) -> None:
        """Save or update a whale's Smart Money Score."""
        import json as _json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO whale_scores
                (address, total_score, roi_score, discipline_score, precision_score,
                 timing_score, tier, tags, trade_count, details, win_rate, roi_perf, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                address.lower(),
                score_data.get("total_score", 50),
                score_data.get("roi_score", 50),
                score_data.get("discipline_score", 50),
                score_data.get("precision_score", 50),
                score_data.get("timing_score", 50),
                score_data.get("tier", "UNRATED"),
                _json.dumps(score_data.get("tags", [])),
                score_data.get("trade_count", 0),
                _json.dumps(score_data.get("details", {})),
                score_data.get("win_rate", 0.0),
                score_data.get("roi_perf", 0.0),
            ))
    
    def get_whale_score(self, address: str) -> Optional[dict]:
        """Get a whale's Smart Money Score."""
        import json as _json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM whale_scores WHERE LOWER(address) = LOWER(?)",
                (address,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "address": row["address"],
                "total_score": row["total_score"],
                "roi_score": row["roi_score"],
                "discipline_score": row["discipline_score"],
                "precision_score": row["precision_score"],
                "timing_score": row["timing_score"],
                "tier": row["tier"],
                "tags": _json.loads(row["tags"]) if row["tags"] else [],
                "trade_count": row["trade_count"],
                "details": _json.loads(row["details"]) if row["details"] else {},
                "win_rate": row["win_rate"] if "win_rate" in row.keys() else 0.0,
                "roi_perf": row["roi_perf"] if "roi_perf" in row.keys() else 0.0,
            }
    
    def get_all_whale_scores(self) -> list[dict]:
        """Get all stored whale scores."""
        import json as _json
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM whale_scores ORDER BY total_score DESC")
            return [
                {
                    "address": row["address"],
                    "total_score": row["total_score"],
                    "roi_score": row["roi_score"],
                    "discipline_score": row["discipline_score"],
                    "precision_score": row["precision_score"],
                    "timing_score": row["timing_score"],
                    "tier": row["tier"],
                    "tags": _json.loads(row["tags"]) if row["tags"] else [],
                    "trade_count": row["trade_count"],
                    "details": _json.loads(row["details"]) if row["details"] else {},
                    "win_rate": row["win_rate"] if "win_rate" in row.keys() else 0.0,
                    "roi_perf": row["roi_perf"] if "roi_perf" in row.keys() else 0.0,
                }
                for row in cursor.fetchall()
            ]


# Singleton instance
db_service = DatabaseService()
