"""
權證分析 API - Flask 主程式
"""

from flask import Flask, request, jsonify
from scraper import WarrantScraper
from analyzer import WarrantAnalyzer
from calculator import ProfitCalculator

app = Flask(__name__)

scraper = WarrantScraper()
analyzer = WarrantAnalyzer()
calculator = ProfitCalculator()


@app.route('/')
def home():
    return jsonify({
        'service': '台灣權證分析 API',
        'version': '1.0.0',
        'endpoints': {
            '/api/search': '搜尋權證',
            '/api/analyze': '單檔分析',
            '/api/health': '健康檢查',
        }
    })


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': '服務正常運作中'})


@app.route('/api/search', methods=['GET', 'POST'])
def search():
    """搜尋權證"""
    if request.method == 'POST':
        data = request.get_json() or {}
        stock_code = data.get('stock_code') or request.args.get('stock_code')
        wtype = data.get('type') or request.args.get('type', 'call')
    else:
        stock_code = request.args.get('stock_code')
        wtype = request.args.get('type', 'call')
    
    if not stock_code:
        return jsonify({'success': False, 'error': '請提供股票代號 stock_code'}), 400
    
    stock_code = str(stock_code).strip()
    wtype = 'call' if wtype.lower() in ['call', 'c', '認購', '看漲'] else 'put'
    
    try:
        stock_info = scraper.get_stock_info(stock_code)
        stock_price = stock_info.get('price')
        
        warrants = scraper.search_warrants(stock_code, wtype)
        
        if not warrants:
            return jsonify({
                'success': True,
                'stock': stock_info,
                'type': wtype,
                'type_name': '認購' if wtype == 'call' else '認售',
                'count': 0,
                'warrants': [],
                'summary': f"找不到 {stock_code} 的{'認購' if wtype == 'call' else '認售'}權證"
            })
        
        analyzed = analyzer.analyze_warrants(warrants, wtype, stock_price)
        
        result = {
            'success': True,
            'stock': stock_info,
            'type': wtype,
            'type_name': '認購' if wtype == 'call' else '認售',
            'count': len(analyzed),
            'warrants': analyzed,
        }
        
        result['summary'] = _format_search_summary(result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze', methods=['GET', 'POST'])
def analyze():
    """單檔分析 + 損益試算"""
    if request.method == 'POST':
        data = request.get_json() or {}
        stock_code = data.get('stock_code') or request.args.get('stock_code')
        warrant_code = data.get('warrant_code') or request.args.get('warrant_code')
        wtype = data.get('type') or request.args.get('type', 'call')
        lots = data.get('lots') or request.args.get('lots', 10)
    else:
        stock_code = request.args.get('stock_code')
        warrant_code = request.args.get('warrant_code')
        wtype = request.args.get('type', 'call')
        lots = request.args.get('lots', 10)
    
    if not stock_code:
        return jsonify({'success': False, 'error': '請提供股票代號'}), 400
    
    stock_code = str(stock_code).strip()
    wtype = 'call' if wtype.lower() in ['call', 'c', '認購', '看漲'] else 'put'
    lots = int(lots) if lots else 10
    
    try:
        stock_info = scraper.get_stock_info(stock_code)
        stock_price = stock_info.get('price')
        
        if not stock_price:
            return jsonify({'success': False, 'error': '無法取得股價'}), 500
        
        warrants = scraper.search_warrants(stock_code, wtype)
        
        target = None
        
        if warrant_code:
            warrant_code = str(warrant_code).strip()
            for w in warrants:
                if w.get('code', '') == warrant_code:
                    target = w
                    break
        
        if not target and warrants:
            analyzed = analyzer.analyze_warrants(warrants, wtype, stock_price)
            target = analyzed[0] if analyzed else None
        
        if not target:
            return jsonify({
                'success': False,
                'error': '找不到符合條件的權證'
            }), 404
        
        target = analyzer.analyze_single(target, wtype, stock_price)
        
        profit_result = calculator.calculate(target, stock_price, lots)
        profit_text = calculator.format_table(profit_result)
        
        result = {
            'success': True,
            'stock': stock_info,
            'warrant': target,
            'profit_table': profit_result,
            'profit_text': profit_text,
        }
        
        result['summary'] = _format_analyze_summary(result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _format_search_summary(result):
    """格式化搜尋摘要"""
    lines = []
    stock = result.get('stock', {})
    
    lines.append(f"📊 {stock.get('code')} {stock.get('name')}")
    lines.append(f"💰 股價：{stock.get('price')} 元")
    lines.append(f"📋 類型：{result.get('type_name')}權證")
    lines.append(f"🎯 推薦：{result.get('count')} 檔")
    lines.append("═" * 30)
    
    for i, w in enumerate(result.get('warrants', [])[:15], 1):
        lines.append(f"\n【{i}】{w.get('code')} {w.get('name')}")
        lines.append(f"發行：{w.get('issuer')} | 履約價：{w.get('strike_price')}")
        lines.append(f"到期：{w.get('expiry_date')} ({w.get('days_left')}天)")
        lines.append(f"價格：{w.get('warrant_price')}元 | 價差：{w.get('spread_pct')}%")
        lines.append(f"槓桿：{w.get('leverage')}x | IV：{w.get('iv')}%")
        lines.append(f"📈 評分：{w.get('score')}分 {w.get('recommendation')}")
        
        for r in w.get('reasons', [])[:3]:
            lines.append(f"   {r}")
    
    return "\n".join(lines)


def _format_analyze_summary(result):
    """格式化分析摘要"""
    lines = []
    stock = result.get('stock', {})
    w = result.get('warrant', {})
    
    lines.append("═" * 35)
    lines.append("📊 權證分析報告")
    lines.append("═" * 35)
    lines.append(f"標的：{stock.get('code')} {stock.get('name')}")
    lines.append(f"現價：{stock.get('price')} 元")
    lines.append("")
    lines.append(f"🎯 {w.get('code')} {w.get('name')}")
    lines.append(f"發行商：{w.get('issuer')}")
    lines.append(f"類型：{'認購' if w.get('type') == 'call' else '認售'}")
    lines.append(f"履約價：{w.get('strike_price')} 元")
    lines.append(f"到期日：{w.get('expiry_date')} ({w.get('days_left')}天)")
    lines.append(f"權證價：{w.get('warrant_price')} 元")
    lines.append(f"價差：{w.get('spread_pct')}%")
    lines.append(f"槓桿：{w.get('leverage')}x")
    lines.append(f"IV：{w.get('iv')}%")
    lines.append("")
    lines.append(f"📈 評分：{w.get('score')}分")
    lines.append(f"🎯 建議：{w.get('recommendation')}")
    
    for r in w.get('reasons', []):
        lines.append(f"   {r}")
    
    lines.append("")
    lines.append(result.get('profit_text', ''))
    
    return "\n".join(lines)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
