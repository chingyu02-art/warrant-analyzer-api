"""
權證分析設定檔
"""

# ===== 認購權證篩選條件 =====
CALL_FILTER = {
    'moneyness_min': -10,
    'moneyness_max': 10,
    'days_min': 60,
    'days_preferred': 90,
    'leverage_min': 3,
    'leverage_max': 8,
    'spread_max': 2.0,
    'price_min': 0.5,
    'price_preferred': 1.0,
}

# ===== 認售權證篩選條件 =====
PUT_FILTER = {
    'moneyness_min': -10,
    'moneyness_max': 10,
    'days_min': 60,
    'days_preferred': 90,
    'leverage_min': 3,
    'leverage_max': 8,
    'spread_max': 3.0,
    'price_min': 0.5,
    'price_preferred': 1.0,
}

# ===== 評分權重 (總和 100) =====
SCORE_WEIGHTS = {
    'days': 20,
    'moneyness': 20,
    'leverage': 15,
    'spread': 20,
    'price': 10,
    'iv': 15,
}

# ===== 損益試算設定 =====
SIMULATION = {
    'default_lots': 10,
    'time_decay_days': [0, 10, 20, 30],
    'price_change_pcts': [15, 10, 5, 0, -5, -10, -15],
}

# ===== 顯示設定 =====
DISPLAY = {
    'top_n': 15,
}
