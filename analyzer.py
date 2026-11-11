"""
權證分析與評分模組
"""

from config import CALL_FILTER, PUT_FILTER, SCORE_WEIGHTS, DISPLAY


class WarrantAnalyzer:
    """權證分析器"""
    
    def analyze_warrants(self, warrants, warrant_type='call', stock_price=None):
        """分析權證並排序，回傳前15檔推薦"""
        if not warrants:
            return []
        
        config = CALL_FILTER if warrant_type == 'call' else PUT_FILTER
        
        iv_values = [w.get('iv') for w in warrants if w.get('iv')]
        iv_stats = {
            'min': min(iv_values) if iv_values else 20,
            'max': max(iv_values) if iv_values else 80,
        }
        iv_stats['range'] = max(iv_stats['max'] - iv_stats['min'], 1)
        
        analyzed = []
        
        for w in warrants:
            if stock_price and w.get('strike_price'):
                w['moneyness'] = self._calc_moneyness(
                    stock_price, w['strike_price'], warrant_type
                )
            else:
                w['moneyness'] = 0
            
            passed, reasons = self._check_filter(w, config)
            
            if not passed:
                continue
            
            score, details = self._calc_score(w, config, iv_stats)
            w['score'] = score
            w['score_details'] = details
            w['recommendation'], w['reasons'] = self._get_recommendation(score, details)
            
            analyzed.append(w)
        
        analyzed.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return analyzed[:DISPLAY['top_n']]
    
    def analyze_single(self, warrant, warrant_type='call', stock_price=None):
        """分析單一權證"""
        result = self.analyze_warrants([warrant], warrant_type, stock_price)
        return result[0] if result else warrant
    
    def _calc_moneyness(self, stock_price, strike_price, warrant_type):
        """計算價內外%"""
        if warrant_type == 'call':
            m = ((stock_price - strike_price) / strike_price) * 100
        else:
            m = ((strike_price - stock_price) / strike_price) * 100
        return round(m, 2)
    
    def _check_filter(self, w, config):
        """篩選條件檢查"""
        reasons = []
        
        days = w.get('days_left') or 0
        if days < config['days_min']:
            reasons.append(f"天數不足({days}天)")
        
        m = w.get('moneyness') or 0
        if m < config['moneyness_min']:
            reasons.append(f"深度價外({m:.1f}%)")
        elif m > config['moneyness_max']:
            reasons.append(f"深度價內({m:.1f}%)")
        
        lev = abs(w.get('leverage') or 0)
        if lev > 0:
            if lev < config['leverage_min']:
                reasons.append(f"槓桿過低({lev:.1f}x)")
            elif lev > config['leverage_max']:
                reasons.append(f"槓桿過高({lev:.1f}x)")
        
        spread = w.get('spread_pct') or 0
        if spread > config['spread_max']:
            reasons.append(f"價差過大({spread:.1f}%)")
        
        price = w.get('warrant_price') or 0
        if price < config['price_min']:
            reasons.append(f"價格過低({price}元)")
        
        return len(reasons) == 0, reasons
    
    def _calc_score(self, w, config, iv_stats):
        """計算評分"""
        details = {}
        
        days = w.get('days_left') or 0
        if days >= 120:
            details['days'] = 100
        elif days >= 90:
            details['days'] = 90
        elif days >= 60:
            details['days'] = 70
        else:
            details['days'] = 50
        
        m = abs(w.get('moneyness') or 10)
        if m <= 2:
            details['moneyness'] = 100
        elif m <= 5:
            details['moneyness'] = 90
        elif m <= 8:
            details['moneyness'] = 75
        else:
            details['moneyness'] = 60
        
        lev = abs(w.get('leverage') or 5)
        if 4 <= lev <= 6:
            details['leverage'] = 100
        elif 3 <= lev <= 8:
            details['leverage'] = 80
        else:
            details['leverage'] = 55
        
        spread = w.get('spread_pct') or 2
        if spread <= 0.8:
            details['spread'] = 100
        elif spread <= 1.2:
            details['spread'] = 90
        elif spread <= 1.5:
            details['spread'] = 80
        elif spread <= 2.0:
            details['spread'] = 70
        else:
            details['spread'] = 55
        
        price = w.get('warrant_price') or 0
        if price >= 2:
            details['price'] = 100
        elif price >= 1:
            details['price'] = 85
        elif price >= 0.5:
            details['price'] = 65
        else:
            details['price'] = 45
        
        iv = w.get('iv') or 50
        percentile = (iv - iv_stats['min']) / iv_stats['range']
        details['iv'] = round(100 - percentile * 40)
        
        total = sum(
            details[k] * SCORE_WEIGHTS[k] / 100
            for k in details
        )
        
        return round(total), details
    
    def _get_recommendation(self, score, details):
        """產生建議"""
        reasons = []
        
        if details.get('days', 0) >= 90:
            reasons.append("✅ 天數充足")
        if details.get('moneyness', 0) >= 90:
            reasons.append("✅ 接近價平")
        if details.get('spread', 0) >= 85:
            reasons.append("✅ 價差小")
        if details.get('iv', 0) >= 80:
            reasons.append("✅ IV相對低")
        if details.get('leverage', 0) >= 80:
            reasons.append("✅ 槓桿適中")
        
        if details.get('days', 0) < 70:
            reasons.append("⚠️ 注意時間流失")
        if details.get('spread', 0) < 70:
            reasons.append("⚠️ 價差偏大")
        if details.get('iv', 0) < 60:
            reasons.append("⚠️ IV偏高")
        
        if score >= 85:
            rec = "⭐ 強力推薦"
        elif score >= 75:
            rec = "👍 推薦"
        elif score >= 65:
            rec = "🔸 可考慮"
        elif score >= 50:
            rec = "⚠️ 普通"
        else:
            rec = "❌ 不建議"
        
        return rec, reasons
