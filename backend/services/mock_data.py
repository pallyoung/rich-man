"""Mock data generators for when AKShare is unavailable."""

import random
from datetime import datetime, timedelta


def generate_kline(code, days=250, base_price=None):
    """Generate realistic mock K-line data."""
    random.seed(hash(code))
    if base_price is None:
        base_price = random.uniform(5, 100)

    data = []
    price = base_price
    current_date = datetime.now()

    for i in range(days, 0, -1):
        date = current_date - timedelta(days=i)
        if date.weekday() >= 5:
            continue

        change_pct = random.gauss(0, 0.025)
        price = price * (1 + change_pct)
        high = price * (1 + abs(random.gauss(0, 0.01)))
        low = price * (1 - abs(random.gauss(0, 0.01)))
        open_price = price * (1 + random.gauss(0, 0.005))
        volume = random.uniform(50000, 500000) * (1 + abs(change_pct) * 10)

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'close': round(price, 2),
            'high': round(max(high, open_price, price), 2),
            'low': round(min(low, open_price, price), 2),
            'volume': int(volume),
            'amount': round(volume * price, 2),
            'change_pct': round(change_pct * 100, 2),
            'change': round(price * change_pct, 2),
            'turnover_rate': round(random.uniform(0.5, 8.0), 2),
        })

    return data


MOCK_STOCKS = [
    {'code': '000001', 'name': '平安银行', 'industry': '银行', 'base': 12.5},
    {'code': '000002', 'name': '万科A', 'industry': '房地产', 'base': 8.2},
    {'code': '000063', 'name': '中兴通讯', 'industry': '通信设备', 'base': 28.5},
    {'code': '000333', 'name': '美的集团', 'industry': '家用电器', 'base': 62.0},
    {'code': '000651', 'name': '格力电器', 'industry': '家用电器', 'base': 38.0},
    {'code': '000725', 'name': '京东方A', 'industry': '面板', 'base': 4.5},
    {'code': '000858', 'name': '五粮液', 'industry': '白酒', 'base': 155.0},
    {'code': '002230', 'name': '科大讯飞', 'industry': '人工智能', 'base': 52.0},
    {'code': '002415', 'name': '海康威视', 'industry': '安防', 'base': 32.0},
    {'code': '002594', 'name': '比亚迪', 'industry': '新能源汽车', 'base': 245.0},
    {'code': '300059', 'name': '东方财富', 'industry': '互联网券商', 'base': 16.0},
    {'code': '300750', 'name': '宁德时代', 'industry': '锂电池', 'base': 195.0},
    {'code': '600000', 'name': '浦发银行', 'industry': '银行', 'base': 7.8},
    {'code': '600009', 'name': '上海机场', 'industry': '机场', 'base': 45.0},
    {'code': '600016', 'name': '民生银行', 'industry': '银行', 'base': 4.2},
    {'code': '600028', 'name': '中国石化', 'industry': '石油', 'base': 5.5},
    {'code': '600030', 'name': '中信证券', 'industry': '证券', 'base': 21.0},
    {'code': '600036', 'name': '招商银行', 'industry': '银行', 'base': 35.0},
    {'code': '600048', 'name': '保利发展', 'industry': '房地产', 'base': 10.5},
    {'code': '600050', 'name': '中国联通', 'industry': '运营商', 'base': 5.8},
    {'code': '600104', 'name': '上汽集团', 'industry': '汽车', 'base': 14.0},
    {'code': '600276', 'name': '恒瑞医药', 'industry': '医药', 'base': 42.0},
    {'code': '600309', 'name': '万华化学', 'industry': '化工', 'base': 85.0},
    {'code': '600519', 'name': '贵州茅台', 'industry': '白酒', 'base': 1680.0},
    {'code': '600585', 'name': '海螺水泥', 'industry': '水泥', 'base': 25.0},
    {'code': '600690', 'name': '海尔智家', 'industry': '家用电器', 'base': 28.0},
    {'code': '600887', 'name': '伊利股份', 'industry': '乳业', 'base': 30.0},
    {'code': '600900', 'name': '长江电力', 'industry': '电力', 'base': 22.0},
    {'code': '601012', 'name': '隆基绿能', 'industry': '光伏', 'base': 22.0},
    {'code': '601088', 'name': '中国神华', 'industry': '煤炭', 'base': 32.0},
    {'code': '601166', 'name': '兴业银行', 'industry': '银行', 'base': 17.0},
    {'code': '601318', 'name': '中国平安', 'industry': '保险', 'base': 48.0},
    {'code': '601398', 'name': '工商银行', 'industry': '银行', 'base': 5.2},
    {'code': '601628', 'name': '中国人寿', 'industry': '保险', 'base': 32.0},
    {'code': '601668', 'name': '中国建筑', 'industry': '建筑', 'base': 5.8},
    {'code': '601688', 'name': '华泰证券', 'industry': '证券', 'base': 16.0},
    {'code': '601857', 'name': '中国石油', 'industry': '石油', 'base': 8.5},
    {'code': '601888', 'name': '中国中免', 'industry': '免税', 'base': 82.0},
    {'code': '603259', 'name': '药明康德', 'industry': 'CXO', 'base': 55.0},
    {'code': '688981', 'name': '中芯国际', 'industry': '半导体', 'base': 48.0},
]


def generate_ranking(rank_type='rise', page=1, page_size=20):
    """Generate mock stock ranking data."""
    random.seed(42)
    stocks = []
    for s in MOCK_STOCKS:
        change_pct = round(random.uniform(-5, 5), 2)
        stocks.append({
            'code': s['code'],
            'name': s['name'],
            'price': round(s['base'] * (1 + change_pct / 100), 2),
            'change': round(s['base'] * change_pct / 100, 2),
            'change_pct': change_pct,
            'volume': round(random.uniform(50000, 2000000)),
            'turnover': round(random.uniform(1e8, 5e10), 2),
            'turnover_rate': round(random.uniform(0.5, 8.0), 2),
            'pe': round(random.uniform(5, 80), 2),
            'market_cap': round(random.uniform(1e10, 2e12), 2),
        })

    if rank_type == 'rise':
        stocks.sort(key=lambda x: x['change_pct'], reverse=True)
    elif rank_type == 'fall':
        stocks.sort(key=lambda x: x['change_pct'])
    elif rank_type == 'turnover':
        stocks.sort(key=lambda x: x['turnover'], reverse=True)
    elif rank_type == 'volume':
        stocks.sort(key=lambda x: x['volume'], reverse=True)

    total = len(stocks)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'stocks': stocks[start:end],
    }


MOCK_SECTORS = [
    {'name': '半导体', 'change': 3.2, 'up': 45, 'down': 8, 'lead': '中芯国际'},
    {'name': '人工智能', 'change': 2.8, 'up': 38, 'down': 12, 'lead': '科大讯飞'},
    {'name': '新能源汽车', 'change': 2.1, 'up': 32, 'down': 15, 'lead': '比亚迪'},
    {'name': '锂电池', 'change': 1.8, 'up': 28, 'down': 10, 'lead': '宁德时代'},
    {'name': '光伏', 'change': 1.5, 'up': 25, 'down': 18, 'lead': '隆基绿能'},
    {'name': '白酒', 'change': 1.2, 'up': 15, 'down': 5, 'lead': '贵州茅台'},
    {'name': '医药', 'change': 0.8, 'up': 55, 'down': 42, 'lead': '恒瑞医药'},
    {'name': '银行', 'change': 0.5, 'up': 28, 'down': 12, 'lead': '招商银行'},
    {'name': '证券', 'change': 0.3, 'up': 30, 'down': 20, 'lead': '中信证券'},
    {'name': '房地产', 'change': -0.2, 'up': 22, 'down': 35, 'lead': '保利发展'},
    {'name': '家用电器', 'change': 0.6, 'up': 18, 'down': 10, 'lead': '美的集团'},
    {'name': '食品饮料', 'change': 0.9, 'up': 35, 'down': 20, 'lead': '伊利股份'},
    {'name': '电力', 'change': 1.1, 'up': 20, 'down': 8, 'lead': '长江电力'},
    {'name': '煤炭', 'change': -0.5, 'up': 10, 'down': 22, 'lead': '中国神华'},
    {'name': '石油化工', 'change': -0.8, 'up': 12, 'down': 25, 'lead': '中国石油'},
    {'name': '通信设备', 'change': 1.9, 'up': 22, 'down': 10, 'lead': '中兴通讯'},
    {'name': '互联网券商', 'change': 2.5, 'up': 8, 'down': 3, 'lead': '东方财富'},
    {'name': '安防', 'change': 1.3, 'up': 15, 'down': 8, 'lead': '海康威视'},
    {'name': 'CXO', 'change': -1.2, 'up': 8, 'down': 18, 'lead': '药明康德'},
    {'name': '汽车零部件', 'change': 1.7, 'up': 40, 'down': 22, 'lead': '均胜电子'},
]


def generate_sectors():
    """Generate mock sector data."""
    sectors = []
    for i, s in enumerate(MOCK_SECTORS):
        sectors.append({
            'code': f'BK{i:04d}',
            'name': s['name'],
            'change_pct': s['change'],
            'market_cap': round(random.uniform(5e11, 5e12), 2),
            'turnover_rate': round(random.uniform(1.0, 5.0), 2),
            'up_count': s['up'],
            'down_count': s['down'],
            'leading_stock': s['lead'],
            'leading_change_pct': round(s['change'] + random.uniform(1, 4), 2),
        })
    return sectors


def generate_fundamental(code):
    """Generate mock fundamental data."""
    stock = next((s for s in MOCK_STOCKS if s['code'] == code), None)
    if not stock:
        stock = {'code': code, 'name': f'股票{code}', 'industry': '未知', 'base': 20.0}

    return {
        'code': code,
        'name': stock['name'],
        'industry': stock['industry'],
        'market_cap': round(random.uniform(5e10, 2e12), 2),
        'float_market_cap': round(random.uniform(3e10, 1.5e12), 2),
        'pe_dynamic': round(random.uniform(8, 60), 2),
        'pb': round(random.uniform(0.8, 8), 2),
        'total_shares': f'{random.randint(5, 200)}亿',
        'float_shares': f'{random.randint(3, 150)}亿',
        'listing_date': f'{random.randint(1995, 2022)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
        'roe': f'{round(random.uniform(5, 30), 2)}%',
        'revenue': f'{round(random.uniform(100, 10000), 2)}亿',
        'net_profit': f'{round(random.uniform(10, 2000), 2)}亿',
    }


def generate_trend_signals(count=20):
    """Generate mock trend signals."""
    signals = []
    signal_types = [
        ('MACD金叉', 'buy', 'MACD线上穿信号线'),
        ('MACD死叉', 'sell', 'MACD线下穿信号线'),
        ('KDJ金叉', 'buy', 'K线上穿D线'),
        ('KDJ死叉', 'sell', 'K线下穿D线'),
        ('RSI超卖反弹', 'buy', 'RSI从30以下回升'),
        ('RSI超买回落', 'sell', 'RSI从70以上回落'),
        ('均线多头排列', 'buy', '5/10/20日均线多头排列'),
        ('均线空头排列', 'sell', '5/10/20日均线空头排列'),
        ('突破布林上轨', 'sell', '价格突破布林带上轨'),
        ('跌破布林下轨', 'buy', '价格跌破布林带下轨'),
    ]

    random.seed(99)
    for i in range(count):
        stock = random.choice(MOCK_STOCKS)
        sig = random.choice(signal_types)
        date = datetime.now() - timedelta(days=random.randint(0, 5))
        strength = random.choice(['强', '中', '弱'])

        signals.append({
            'code': stock['code'],
            'name': stock['name'],
            'signal_type': sig[0],
            'direction': sig[1],
            'description': sig[2],
            'strength': strength,
            'date': date.strftime('%Y-%m-%d'),
            'price': round(stock['base'] * random.uniform(0.9, 1.1), 2),
        })

    signals.sort(key=lambda x: x['date'], reverse=True)
    return signals
