"""
测试 futu_client.get_basicfiltered_stocks() 返回值
"""
import pandas as pd
from data.sources.futu_client import FutuAPIClient
from utils.settings import settings


def test_get_basicfiltered_stocks():
    """测试 get_basicfiltered_stocks 方法的返回值"""
    print("=== 测试 get_basicfiltered_stocks ===")

    config = settings.data.futu

    client = FutuAPIClient(config)

    print("正在连接 Futu API...")
    connected = client.connect()

    if not connected:
        print("X Futu 客户端连接失败")
        return

    print("OK Futu 客户端连接成功")

    print("\n调用 get_basicfiltered_stocks()...")
    result = client.get_basicfiltered_stocks()

    print(f"\n返回结果:")
    print(f"  type(result): {type(result)}")
    print(f"  result: {result}")

    if result:
        print(f"\n详细分析:")
        print(f"  len(result): {len(result)}")
        if len(result) >= 1:
            print(f"  result[0] (success): {result[0]} (type: {type(result[0])})")
        if len(result) >= 2:
            print(f"  result[1] (filtered_list): {result[1]} (type: {type(result[1])})")
        if len(result) >= 3:
            print(f"  result[2] (name_dict): {result[2]} (type: {type(result[2])})")

        # 测试遍历
        if len(result) >= 3:
            _, filtered_list, name_dict = result
            print(f"\n尝试遍历 filtered_list:")
            try:
                for code in filtered_list:
                    print(f"  {code}: {name_dict.get(code, '')}")
                print("OK 遍历成功")
            except Exception as e:
                print(f"X 遍历失败: {e}")
    else:
        print("X result 为空/False")

    # 断开连接
    client.disconnect()
    print("\n连接已断开")


if __name__ == "__main__":
    test_get_basicfiltered_stocks()
