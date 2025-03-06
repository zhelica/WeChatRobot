# 免费数据源
import akshare as ak  # 推荐使用（全面且稳定）
import tushare as ts  # 需要注册token
import re

# 付费数据源（机构级）
# 通联数据、万得（Wind）、东方财富Choice
# 示例1：获取沪深300成分股
# hs300 = ak.stock_zh_index_spot_sina()  # 实时行情
# print(hs300)
# hs300_list = ak.index_stock_cons('000300')  # 成分股列表
# print(hs300_list)

# 示例2：获取个股历史数据（前复权）
# df = ak.stock_zh_a_daily(
#     symbol="sh600519",
#     adjust="qfq",  # qfq前复权 hfq后复权
#     start_date="20250305"
# )
# print(df)
#
# 定义股票代码
# symbol = "sh600519"  # 贵州茅台的股票代码

#获取实时行情数据
# name="股票查询贵州茅台"
# stock_real_time_data = ak.stock_zh_a_spot_em()
# filtered_data = stock_real_time_data[stock_real_time_data['名称']== '贵州茅台']
# # 打印结果
# print(filtered_data)

# # 示例3：获取财务数据
# balance_sheet = ak.stock_financial_report_sina(stock="600519", symbol="资产负债表")
# print(balance_sheet)

def extract_stock_name(query_string):
    """
    从查询字符串中提取股票名称。

    参数:
    query_string (str): 包含查询指令和股票名称的字符串，例如'股票查询贵州茅台'。

    返回:
    str: 提取出的股票名称。
    """
    # 假设查询指令固定为“股票查询”，可以根据实际情况调整
    prefix = "股票查询"

    # 检查字符串是否以指定前缀开头
    if not query_string.startswith(prefix):
        raise ValueError("查询字符串格式不正确，应以'股票查询'开头")

    # 截取查询指令之后的部分作为股票名称
    stock_name = query_string[len(prefix):].strip()

    return stock_name


def format_stock_info(stock_data):
    """
    格式化股票信息。

    参数:
    stock_data (pandas.Series): 单个股票的数据。

    返回:
    str: 格式化后的股票信息字符串。
    """
    formatted_info = (
        f"代码 {stock_data['代码']}\n"
        f"名称 {stock_data['名称']}\n"
        f"最新价 {stock_data['最新价']}\n"
        f"涨速 {stock_data['涨速']}\n"
        f"5分钟涨跌 {stock_data['5分钟涨跌']}\n"
        f"60日涨跌幅 {stock_data['60日涨跌幅']}\n"
        f"年初至今涨跌幅 {stock_data['年初至今涨跌幅']}"
    )
    return formatted_info


def query_stock_by_query_string(query_string):
    """
    根据查询字符串中的股票名称查询A股市场实时行情数据。

    参数:
    query_string (str): 包含查询指令和股票名称的字符串，例如'股票查询贵州茅台'。

    返回:
    str: 包含符合条件的股票实时行情数据的格式化字符串。
    """
    try:
        # 从查询字符串中提取股票名称
        stock_name = extract_stock_name(query_string)

        # 获取A股市场实时行情数据
        stock_real_time_data = ak.stock_zh_a_spot_em()

        # 过滤出指定名称的股票数据
        filtered_data = stock_real_time_data[stock_real_time_data['名称'] == stock_name]

        # 如果没有找到匹配的数据或发生了错误
        if filtered_data is None or filtered_data.empty:
            return "没有找到匹配的数据。"

        # 格式化并拼接所有符合条件的股票信息
        result_str = ""
        for _, row in filtered_data.iterrows():
            result_str += format_stock_info(row) + "\n---\n"

        return result_str.strip()  # 移除最后一个多余的换行符和分隔符
    except Exception as e:
        return f"发生错误: {e}"


# 假设 msg 是一个包含 content 属性的对象
# class Message:
#     def __init__(self, content):
#         self.content = content
#
#
# # 示例消息
# msg = Message(content="股票查询贵州茅台")

# # 判断 msg.content 是否以“股票查询”开头
# if msg.content.startswith("股票查询"):
#     result = query_stock_by_query_string(msg.content)
#
#     # 返回结果
#     print(result)  # 或者根据实际需求将结果返回给调用者
# else:
#     print("消息内容不是以'股票查询'开头。")


def extract_index_name(query_string):
    """
    从查询字符串中提取指数名称。

    参数:
    query_string (str): 包含查询指令和指数名称的字符串，例如'指数查询上证指数'。

    返回:
    str: 提取出的指数名称。
    """
    # 假设查询指令固定为“指数查询”，可以根据实际情况调整
    prefix = "指数查询"

    # 检查字符串是否以指定前缀开头
    if not query_string.startswith(prefix):
        raise ValueError("查询字符串格式不正确，应以'指数查询'开头")

    # 截取查询指令之后的部分作为指数名称
    index_name = query_string[len(prefix):].strip()

    return index_name


def format_index_info(index_data):
    """
    格式化指数信息。

    参数:
    index_data (pandas.Series): 单个指数的数据。

    返回:
    str: 格式化后的指数信息字符串。
    """
    formatted_info = (
        f"代码 {index_data['代码']}\n"
        f"名称 {index_data['名称']}\n"
        f"最新价 {index_data['最新价']}\n"
        f"最高 {index_data['最高']}\n"
        f"最低 {index_data['最低']}\n"
        f"成交量 {index_data['成交量'] / 100000000:.2f}亿\n"  # 成交量保留两位小数
        f"成交额 {int(index_data['成交额'] / 100000000)}亿"      # 成交额去除小数部分
    )
    return formatted_info


def query_index_by_query_string(query_string):
    """
    根据查询字符串中的指数名称查询实时行情数据。

    参数:
    query_string (str): 包含查询指令和指数名称的字符串，例如'指数查询上证指数'。

    返回:
    str: 包含符合条件的指数实时行情数据的格式化字符串。
    """
    try:
        # 从查询字符串中提取指数名称
        index_name = extract_index_name(query_string)

        # 获取实时行情数据
        hs300 = ak.stock_zh_index_spot_sina()

        # 过滤出指定名称的指数数据
        filtered_data = hs300[hs300['名称'] == index_name]

        # 如果没有找到匹配的数据或发生了错误
        if filtered_data is None or filtered_data.empty:
            return "没有找到匹配的数据或发生了错误。"

        # 格式化并拼接所有符合条件的指数信息
        result_str = ""
        for _, row in filtered_data.iterrows():
            result_str += format_index_info(row) + "\n---\n"

        return result_str.strip()  # 移除最后一个多余的换行符和分隔符
    except Exception as e:
        return f"发生错误: {e}"


