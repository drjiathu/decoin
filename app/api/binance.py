import requests
import xml.etree.ElementTree as ET

BINANCE_DATA_ROOT = "data.binance.vision/"


def get_binance_futures_symbols() -> list[str]:
    """Get all Binance future symbols"""
    url = "https://s3-ap-northeast-1.amazonaws.com/{BINANCE_DATA_ROOT}"
    params = {"prefix": "data/futures/um/daily/trades/", "delimiter": "/"}

    # 发送HTTP请求获取XML响应
    response = requests.get(url, params=params)
    response.raise_for_status()

    # 解析XML
    root = ET.fromstring(response.text)
    symbols = []

    # 提取所有CommonPrefixes/Prefix节点
    for prefix in root.findall(
        ".//{http://s3.amazonaws.com/doc/2006-03-01/}CommonPrefixes"
    ):
        prefix_node = prefix.find("{http://s3.amazonaws.com/doc/2006-03-01/}Prefix")
        if prefix_node is None or prefix_node.text is None:
            continue
        path = prefix_node.text
        # 从路径中提取币种名称
        parts = path.split("/")
        if len(parts) >= 2:
            symbol = parts[-2]
            symbols.append(symbol)

    return sorted(symbols)


def get_symbol_files(symbol: str) -> list[str]:
    """Get all files for a specific symbol"""
    url = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/"
    params = {"prefix": f"data/futures/um/daily/trades/{symbol}/", "delimiter": "/"}

    response = requests.get(url, params=params)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    files = []

    # Extract all Contents/Key nodes
    for content in root.findall(".//{http://s3.amazonaws.com/doc/2006-03-01/}Contents"):
        key_node = content.find("{http://s3.amazonaws.com/doc/2006-03-01/}Key")
        if key_node is not None and key_node.text is not None:
            files.append(key_node.text)

    return sorted(files)
