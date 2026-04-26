"""
Exposure Calculator Tool.
Calculates sector exposure percentages for a given portfolio.
Only equity (Stock) holdings are considered; bonds are excluded.
Exposure is derived from current_weight in holdings, normalized
to sum to 100% across equity-only holdings.
"""

import logging
import sqlite3
from typing import Any

from database import execute_query

logger = logging.getLogger(__name__)

# SQL to retrieve all equity holdings for a portfolio and their sector info.
# current_weight is the pre-stored portfolio weight for each holding.
# We re-normalize over equity-only holdings to get sector exposure.
_HOLDINGS_SQL = """
SELECT
    sec.sector_name,
    h.current_weight,
    s.symbol,
    s.company_name,
    s.asset_type
FROM holdings h
JOIN securities s ON h.security_id = s.security_id
JOIN sectors sec ON s.sector_id = sec.sector_id
JOIN portfolios p ON h.portfolio_id = p.portfolio_id
WHERE p.portfolio_name = ?
  AND s.asset_type = 'Stock'
ORDER BY sec.sector_name, s.symbol
"""

_PORTFOLIO_EXISTS_SQL = """
SELECT portfolio_id, portfolio_name FROM portfolios WHERE portfolio_name = ?
"""


class ExposureCalculatorTool:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def run(self, portfolio_name: str) -> dict[str, Any]:
        """
        Calculate sector exposures for the given portfolio name.

        Returns:
            {
                "portfolio_name": str,
                "sector_exposures": {sector_name: float (%)},
                "equity_weight_total": float,
                "holdings_detail": list[dict],
                "error": str | None
            }
        """
        logger.info("ExposureCalculatorTool: portfolio=%s", portfolio_name)

        # Verify portfolio exists
        try:
            exists = self.conn.execute(
                _PORTFOLIO_EXISTS_SQL, (portfolio_name,)
            ).fetchone()
        except Exception as exc:
            return self._error(portfolio_name, f"Database error: {exc}")

        if not exists:
            return self._error(
                portfolio_name,
                f"Portfolio not found: '{portfolio_name}'. "
                "Check the exact name and try again.",
            )

        # Fetch equity holdings
        try:
            cursor = self.conn.execute(_HOLDINGS_SQL, (portfolio_name,))
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception as exc:
            return self._error(portfolio_name, f"Query error: {exc}")

        if not rows:
            return self._error(
                portfolio_name,
                f"No equity holdings found for portfolio '{portfolio_name}'.",
            )

        # Sum weights of equity holdings (may not sum to 1.0 if portfolio has bonds)
        equity_weight_total = sum(
            float(r["current_weight"]) for r in rows if r["current_weight"] is not None
        )

        if equity_weight_total == 0:
            return self._error(
                portfolio_name,
                "Total equity weight is zero; cannot compute exposure.",
            )

        # Aggregate by sector
        sector_raw: dict[str, float] = {}
        for row in rows:
            sector = row["sector_name"]
            weight = float(row["current_weight"]) if row["current_weight"] else 0.0
            sector_raw[sector] = sector_raw.get(sector, 0.0) + weight

        # Normalize to percentages (relative to equity-only total)
        sector_exposures = {
            sector: round((w / equity_weight_total) * 100, 2)
            for sector, w in sorted(
                sector_raw.items(), key=lambda x: x[1], reverse=True
            )
        }

        return {
            "portfolio_name": portfolio_name,
            "sector_exposures": sector_exposures,
            "equity_weight_total": round(equity_weight_total, 4),
            "holdings_detail": rows,
            "error": None,
        }

    @staticmethod
    def _error(portfolio_name: str, message: str) -> dict[str, Any]:
        logger.error("ExposureCalculatorTool error: %s", message)
        return {
            "portfolio_name": portfolio_name,
            "sector_exposures": {},
            "equity_weight_total": 0.0,
            "holdings_detail": [],
            "error": message,
        }