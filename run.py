import ccxt
import pandas as pd

from app.api.okx import get_all_okx_markets


def get_okx_markets():
    """
    使用 ccxt 获取 OKX 所有交易市场信息
    :return: 包含所有市场信息的 DataFrame
    """
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
        filtered_df = df[
            [
                "id",
                "type",
                "spot",
                "swap",
                "future",  # 基础信息
                "base",
                "quote",
                "baseId",
                "quoteId",  # 币种信息
                "active",
                "precision",
                "limits",  # 状态和限制
                "contract",
                "expiry",
                "expiryDatetime",  # 合约专用字段
                "contractSize",
                "linear",
                "inverse",  # 合约参数
            ]
        ]

        return filtered_df

    except ccxt.NetworkError as e:
        print(f"网络错误: {e}")
    except ccxt.ExchangeError as e:
        print(f"交易所错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
    return pd.DataFrame()


def main():
    markets = get_all_okx_markets()
    markets.to_csv("okx_all_markets.csv", index=False)


# # 获取所有市场数据
# markets_df = get_okx_markets()

# # 按类型分类
# spot_df = markets_df[markets_df["spot"]].copy()  # 现货
# swap_df = markets_df[markets_df["swap"]].copy()  # 永续合约
# futures_df = markets_df[markets_df["future"]].copy()  # 交割合约

# # 保存到 CSV
# markets_df.to_csv("okx_all_markets.csv", index=False)
# print(f"数据已保存，总记录数: {len(markets_df)}")

# # 显示现货市场示例
# print("\n现货市场示例:")
# print(spot_df[["id", "base", "quote", "active"]].head())

# # 显示合约市场示例
# print("\n永续合约示例:")
# print(swap_df[["id", "base", "quote", "contractSize"]].head())

# print("\n交割合约示例:")
# print(futures_df[["id", "base", "quote", "expiryDatetime"]].head())


if __name__ == "__main__":
    main()
