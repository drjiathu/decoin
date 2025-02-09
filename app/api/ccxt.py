import ccxt
import pandas as pd


def get_all_markets(exchange: str):
    """
    使用 ccxt 获取 OKX 所有交易市场的 symbol 和 type 信息
    :return: 包含所有市场信息的 DataFrame
    """
    exchange_names = ccxt.exchanges
    if exchange in exchange_names:
        exchange = ccxt.okx(
            {
                "enableRateLimit": True,  # 启用速率限制（必须）
                # 'proxy': 'http://your-proxy:port'  # 国内访问可能需要代理
            }
        )

    try:
        # 加载所有市场数据（首次调用可能需要网络请求）
        markets = exchange.load_markets()

        # 转换为 DataFrame
        df = pd.DataFrame.from_dict(markets, orient="index")

        # 按类型过滤并重组关键字段
        # filtered_df = df[
        #     [
        #         "id",
        #         "type",
        #         "spot",
        #         "swap",
        #         "future",  # 基础信息
        #         "base",
        #         "quote",
        #         "baseId",
        #         "quoteId",  # 币种信息
        #         "active",
        #         "precision",
        #         "limits",  # 状态和限制
        #         "contract",
        #         "expiry",
        #         "expiryDatetime",  # 合约专用字段
        #         "contractSize",
        #         "linear",
        #         "inverse",  # 合约参数
        #     ]
        # ]

        # return filtered_df
        return df

    except ccxt.NetworkError as e:
        print(f"网络错误: {e}")
    except ccxt.ExchangeError as e:
        print(f"交易所错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
    return pd.DataFrame()
