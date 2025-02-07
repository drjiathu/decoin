import random
import requests
import subprocess
import time


# Shadowsocks 代理配置
SS_CONFIG = {
    "server": "c90s1.portablesubmarines.com",
    "server_port": 19597,
    "password": "",
    "method": "aes-256-gcm",
    "local_port": 1080,  # 本地 SOCKS5 代理端口
}

PROXIES = [
    "23.105.203.52:19597",
]


def get_with_proxy_rotation(url, params):
    proxy = random.choice(PROXIES)
    # try:
    return requests.get(url, params=params, proxies={"http": proxy, "https": proxy})
    # except Exception as e:
    #     print(e)
    #     return None


# 启动 Shadowsocks 客户端
def start_shadowsocks_proxy():
    command = [
        "sslocal",
        "-s",
        SS_CONFIG["server"],
        "-p",
        str(SS_CONFIG["server_port"]),
        "-k",
        SS_CONFIG["password"],
        "-m",
        SS_CONFIG["method"],
        "-l",
        str(SS_CONFIG["local_port"]),
        "-d",
        "start",
    ]
    subprocess.Popen(command)
    time.sleep(2)  # 等待代理启动
