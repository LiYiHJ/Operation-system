"""
API路由包
"""

from .dashboard import dashboard_bp
from .products import products_bp
from .profit import profit_bp
from .strategy import strategy_bp
from .import_route import import_bp
from .ingestion import ingestion_bp

__all__ = [
    'dashboard_bp',
    'products_bp',
    'profit_bp',
    'strategy_bp',
    'import_bp',
    'ingestion_bp',
]
