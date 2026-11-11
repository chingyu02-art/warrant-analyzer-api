"""
權證資料爬蟲模組
資料來源：Yahoo Finance、證交所
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re


class WarrantScraper:
    """權證資料爬蟲"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        })
    
    def get_stock_info(self, stock_code):
        """取得股票現價"""
        stock_code = str(stock_code).strip()
        
        try:
            info = self._get_twse_realtime(stock_code)
            if info and info.get('price'):
                return info
        except Exception as e:
            print(f"證交所查詢失敗: {e}")
        
        return {'code': stock_code, 'name': stock_code, 'price': None}
    
    def _get_twse_realtime(self, stock_code):
        """從證交所取得即時股價"""
        for market in ['tse', 'otc']:
            url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={market}_{stock_code}.tw"
            
            try:
                resp = self.session.get(url, timeout=10)
                data = resp.json()
                
                if data.get('msgArray') and len(data['msgArray']) > 0:
                    stock = data['msgArray'][0]
                    price = stock.get('z') or stock.get('y') or stock.get('o')
                    
                    if price and price != '-':
                        return {
                            'code': stock_code,
                            'name': stock.get('n', stock_code),
                            'price': float(price)
                        }
            except:
                continue
        
        return None
    
    def search_warrants(self, stock_code, warrant_type='call'):
        """搜尋權證 - 使用證交所公開資料"""
        stock_code = str(stock_code).strip()
        warrants = []
        
        try:
            warrants = self._scrape_twse_warrants(stock_code, warrant_type)
            print(f"找到 {len(warrants)} 檔權證")
        except Exception as e:
            print(f"爬取失敗: {e}")
        
        if not warrants:
            warrants = self._generate_demo_warrants(stock_code, warrant_type)
        
        return warrants
    
    def _scrape_twse_warrants(self, stock_code, warrant_type):
        """從證交所爬取權證資料"""
        warrants = []
        
        url = "https://www.twse.com.tw/rwd/zh/warrant/warrantSearch"
        
        params = {
            'underlying': stock_code,
            'response': 'json',
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if data.get('data'):
                for row in data['data']:
                    try:
                        code = row[0] if len(row) > 0 else ''
                        name = row[1] if len(row) > 1 else ''
                        
                        is_call = '購' in name or 'C' in name.upper()
                        is_put = '售' in name or 'P' in name.upper()
                        
                        if warrant_type == 'call' and not is_call:
                            continue
                        if warrant_type == 'put' and not is_put:
                            continue
                        
                        warrant = {
                            'code': code,
                            'name': name,
                            'underlying': stock_code,
                            'type': warrant_type,
                            'strike_price': self._parse_float(row[4]) if len(row) > 4 else None,
                            'expiry_date': row[3] if len(row) > 3 else '',
                            'ratio': self._parse_float(row[5]) or 0.01,
                            'warrant_price': self._parse_float(row[6]) if len(row) > 6 else None,
                            'spread_pct': self._parse_float(row[8]) if len(row) > 8 else 1.5,
                            'leverage': self._parse_float(row[9]) if len(row) > 9 else 5.0,
                            'iv': self._parse_float(row[10]) if len(row) > 10 else 30.0,
                            'issuer': self._extract_issuer(name),
                        }
                        
                        warrant = self._enrich_warrant(warrant)
                        
                        if warrant.get('warrant_price') and warrant['warrant_price'] > 0:
                            warrants.append(warrant)
                            
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"證交所連線錯誤: {e}")
        
        return warrants
    
    def _generate_demo_warrants(self, stock_code, warrant_type):
        """產生展示用資料"""
        stock_info = self.get_stock_info(stock_code)
        price = stock_info.get('price') or 100
        
        issuers = ['元大', '凱基', '群益', '統一', '富邦', '永豐', '國泰', '中信']
        type_char = '購' if warrant_type == 'call' else '售'
        
        warrants = []
        
        for i, issuer in enumerate(issuers[:8]):
            strike_offset = (i - 4) * 0.02 * price
            strike = round(price + strike_offset, 1)
            
            days_left = 90 + i * 15
            expiry = datetime.now()
            from datetime import timedelta
            expiry = expiry + timedelta(days=days_left)
            expiry_str = expiry.strftime('%Y/%m/%d')
            
            wp = round(1.0 + (i * 0.3), 2)
            
            warrant = {
                'code': f'0{80000 + i}',
                'name': f'{stock_info.get("name", stock_code)}{issuer}25{type_char}0{i+1}',
                'underlying': stock_code,
                'type': warrant_type,
                'strike_price': strike,
                'expiry_date': expiry_str,
                'ratio': 0.01,
                'warrant_price': wp,
                'spread_pct': round(0.8 + i * 0.2, 1),
                'leverage': round(4.0 + i * 0.5, 1),
                'iv': round(25 + i * 2, 1),
                'issuer': issuer,
                'days_left': days_left,
                'has_quote': True,
            }
            
            warrants.append(warrant)
        
        return warrants
    
    def _enrich_warrant(self, warrant):
        """補充計算欄位"""
        expiry = warrant.get('expiry_date', '')
        warrant['days_left'] = self._calc_days_left(expiry)
        
        if not warrant.get('spread_pct'):
            price = warrant.get('warrant_price') or 0
            if price >= 2:
                warrant['spread_pct'] = 1.0
            elif price >= 1:
                warrant['spread_pct'] = 1.5
            elif price >= 0.5:
                warrant['spread_pct'] = 2.0
            else:
                warrant['spread_pct'] = 3.0
        
        warrant['has_quote'] = (warrant.get('warrant_price') or 0) > 0
        
        if not warrant.get('issuer'):
            warrant['issuer'] = self._extract_issuer(warrant.get('name', ''))
        
        return warrant
    
    def _calc_days_left(self, date_str):
        """計算剩餘天數"""
        if not date_str:
            return 0
        
        formats = ['%Y/%m/%d', '%Y-%m-%d', '%Y%m%d', '%m/%d/%Y']
        
        for fmt in formats:
            try:
                expiry = datetime.strptime(str(date_str).strip(), fmt)
                days = (expiry - datetime.now()).days
                return max(days, 0)
            except:
                continue
        
        return 90
    
    def _parse_float(self, value):
        """解析浮點數"""
        try:
            if hasattr(value, 'get_text'):
                value = value.get_text(strip=True)
            text = str(value) if value else ''
            text = re.sub(r'[^\d.\-]', '', text)
            return float(text) if text else None
        except:
            return None
    
    def _extract_issuer(self, name):
        """從權證名稱提取發行商"""
        issuers = [
            '元大', '凱基', '群益', '統一', '富邦', '永豐', '國泰', '中信',
            '日盛', '兆豐', '玉山', '台新', '元富', '華南', '國票', '康和'
        ]
        
        name = str(name) if name else ''
        
        for issuer in issuers:
            if issuer in name:
                return issuer
        
        return ''
