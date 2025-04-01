import requests
import time
from datetime import datetime, timedelta
import random
import configparser

def send_get_request(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 如果响应状态码不是200，会抛出HTTPError
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GET request failed: {e}")
        return None


def send_post_request(url, headers, data):
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"POST request failed: {e}")
        return None


def main():
    config = configparser.ConfigParser()
    config.read('config.ini')  # 假设配置文件名为config.ini
    get_url = "https://actionv3.gyyx.cn/pockfun/768pockfun/lottery/pool"
    post_url = "https://actionv3.gyyx.cn/pockfun/768pockfun/lottery/tenTimes"
    headers = {
        'Cookie': config.get('headers', 'cookie'),
        'Content-Type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko'
    }

    while True:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # 检查是否是整点或剩余时间小于15分钟
        if (8 <= current_hour < 20) and (current_minute == 0 or current_minute >= 1):
            print(f"Executing at {now}")
            response_data = send_get_request(get_url, headers)
            print(f"返回参数: {response_data}")
            if response_data is not None:
                dw_value = '笛舞'

                # 使用 next 和生成器表达式快速查找符合条件的奖品
                prize = next((p for p in response_data['data']['poolPrizeVos']
                              if p['pcn'] == dw_value and not p['isWinning']), None)
                #奖品存在 开始抽奖
                if prize:
                    post_data = {
                        "from": "stage",
                        "pc": prize['pc'],
                        "r": random.random()  # 使用随机数生成器
                    }
                    # 打印 post_data 以进行调试
                    print(f"请求参数: {post_data}")

                    # 发送 POST 请求并获取返回结果
                    post_response = send_post_request(post_url, headers, post_data)

                    # 打印返回结果
                    print(f"抽奖结果: {post_response}")

                    if post_response is not None:
                        print(f"Executed POST request for prize: {prize}")
                    else:
                        print("POST request failed")
                else:
                    print("未找到符合条件的奖品或奖品已被领取")

            # # 在每次执行完任务后等待0.5秒，避免过于频繁地发送请求
            # time.sleep(0.1)  # 等待0.5秒

        else:
            # 如果当前不在需要执行的时间段内，等待到下一个检查点
            if current_minute < 45:
                next_check_time = now.replace(minute=45, second=0, microsecond=0)
            else:
                next_check_time = now.replace(hour=current_hour + 1, minute=0, second=0, microsecond=0)

            sleep_seconds = (next_check_time - now).total_seconds()
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()