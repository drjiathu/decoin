import requests
import xml.etree.ElementTree as ET
from typing import List, Dict


def get_subdirectories(base_url: str, prefix: str) -> List[str]:
    """获取指定前缀下的所有子目录"""
    params = {"prefix": prefix, "delimiter": "/"}
    subdirs = []

    while True:
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        root = ET.fromstring(response.text)

        # 处理CommonPrefixes
        for prefix_node in root.findall(
            ".//{http://s3.amazonaws.com/doc/2006-03-01/}CommonPrefixes"
        ):
            prefix_text = prefix_node.find(
                "{http://s3.amazonaws.com/doc/2006-03-01/}Prefix"
            )
            if prefix_text is not None and prefix_text.text is not None:
                subdirs.append(prefix_text.text)

        # 检查是否有更多结果
        is_truncated = root.find(
            ".//{http://s3.amazonaws.com/doc/2006-03-01/}IsTruncated"
        )
        if is_truncated is None or is_truncated.text != "true":
            break

        # 设置下一个分页的marker
        next_marker = root.find(
            ".//{http://s3.amazonaws.com/doc/2006-03-01/}NextMarker"
        )
        if next_marker is None or next_marker.text is None:
            break
        params["marker"] = next_marker.text

    return subdirs


def get_binance_futures_data_structure() -> Dict[str, List[str]]:
    """获取Binance期货交易数据的完整目录结构"""
    base_url = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/"
    result = {}

    # 首先获取所有币种目录
    symbols = get_subdirectories(base_url, "data/futures/um/daily/trades/")

    # 然后获取每个币种下的日期目录
    for symbol_path in symbols:
        symbol = symbol_path.split("/")[-2]
