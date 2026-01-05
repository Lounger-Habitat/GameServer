"""统计模块"""
from .models import *
from .storage import get_stats_store
from .middleware import StatisticsMiddleware
from .routes import router
