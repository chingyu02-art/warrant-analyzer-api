"""
損益試算模組 (含時間價值流失)
"""

import math
from config import SIMULATION


class ProfitCalculator:
    """損益試算器"""
    
    def __init__(self):
        self.rf_rate = 0.015
    
    def calculate(self, warrant, stock_price, lots=None):
        """計算損益試算表"""
        lots = lots or SIMULATION['default_lots']
        
        wp = warrant.get('warrant_price') or 0
        strike = warrant.get('strike_price') or stock_price
        iv = (warrant.get('iv') or 30) / 100
        days = warrant.get('days_left') or 90
        ratio = warrant.get('ratio') or 0.01
        wtype = warrant.get('type', 'call')
        
        cost = wp * lots * 1000
        
        result = {
            'input': {
                'lots': lots,
                'warrant_price': wp,
                'stock_price': stock_price,
                'cost': cost,
                'strike_price': strike,
                'days_left': days,
                'iv': warrant.get('iv'),
                'ratio': ratio,
            },
            'table': []
        }
        
        for pct in SIMULATION['price_change_pcts']:
            target = stock_price * (1 + pct / 100)
            
            row = {
                'change_pct': pct,
                'target_price': round(target, 2),
                'scenarios': []
            }
            
            for d in SIMULATION['time_decay_days']:
                remain = max(days - d, 1)
                
                est = self._bs_price(
                    S=target, K=strike, T=remain/365,
                    r=self.rf_rate, sigma=iv,
                    opt_type=wtype, ratio=ratio
                )
                
                profit = (est - wp) * lots * 1000
                profit_pct = ((est / wp) - 1) * 100 if wp > 0 else 0
                
                row['scenarios'].append({
                    'days': d,
                    'remaining': remain,
                    'est_price': round(est, 2),
                    'profit': round(profit),
                    'profit_pct': round(profit_pct, 1),
                })
            
            result['table'].append(row)
        
        return result
    
    def _bs_price(self, S, K, T, r, sigma, opt_type='call', ratio=0.01):
        """Black-Scholes 定價"""
        if T <= 0:
            if opt_type == 'call':
                return max(S - K, 0) * ratio
            else:
                return max(K - S, 0) * ratio
        
        try:
            d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
            d2 = d1 - sigma*math.sqrt(T)
            
            if opt_type == 'call':
                price = S*self._N(d1) - K*math.exp(-r*T)*self._N(d2)
            else:
                price = K*math.exp(-r*T)*self._N(-d2) - S*self._N(-d1)
            
            return max(price * ratio, 0.01)
        except:
            return 0.01
    
    def _N(self, x):
        """標準常態CDF"""
        return (1 + math.erf(x / math.sqrt(2))) / 2
    
    def format_table(self, result):
        """格式化為文字"""
        lines = []
        inp = result['input']
        
        lines.append("═" * 40)
        lines.append("📊 損益試算表")
        lines.append("═" * 40)
        lines.append(f"買進：{inp['lots']} 張 × {inp['warrant_price']} 元")
        lines.append(f"成本：{inp['cost']:,.0f} 元")
        lines.append(f"標的現價：{inp['stock_price']} 元")
        lines.append(f"履約價：{inp['strike_price']} 元")
        lines.append(f"剩餘：{inp['days_left']} 天 | IV：{inp['iv']}%")
        lines.append("")
        lines.append("股價漲跌 → 預估損益（立即/10天/20天/30天）")
        lines.append("─" * 40)
        
        for row in result['table']:
            pct = row['change_pct']
            target = row['target_price']
            
            profits = []
            for s in row['scenarios']:
                p = s['profit']
                if p >= 0:
                    profits.append(f"+{p:,}")
                else:
                    profits.append(f"{p:,}")
            
            line = f"{pct:+3d}% ({target:.0f}元): {' / '.join(profits)}"
            lines.append(line)
        
        lines.append("─" * 40)
        lines.append("💡 時間越長，時間價值流失越多")
        
        return "\n".join(lines)
