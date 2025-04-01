import pandas as pd
from datetime import datetime, timedelta


def get_duty_info():
    file_path="值班表.xlsx"
    # 创建值班人和ID的映射字典
    person_id_map = {
        "毕研泽": "wxid_c0yjh5nyvk3e22",
        "李哲": "wxid_c0yjh5nyvk3e22",
        # 添加其他人员及其ID
    }

    # 读取Excel文件，并确保日期列被解析为datetime
    df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

    # 获取今天的日期和未来一周的日期范围
    today = datetime.today()
    next_week_dates = [(today + timedelta(days=i)).date() for i in range(1, 8)]  # 转换为仅日期

    # 找到今天的值班信息
    today_str = today.strftime('%Y-%m-%d')
    today_info = df[df['日期'].dt.date == today.date()]  # 比较时不考虑时间部分

    # 将星期几转换为汉字
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    chinese_weekday = weekdays[today.weekday()]

    output = []

    if not today_info.empty:
        on_duty_person = today_info.iloc[0]['值班人']
        on_duty_person_id = person_id_map.get(on_duty_person, '未知')  # 获取值班人的ID，如果没有则默认为'未知'
        remarks_raw = today_info.iloc[0]['备注']
        remarks = remarks_raw if isinstance(remarks_raw, str) and '接口值班' in remarks_raw else ''
        output.append(f"今天的日期：{today_str} 星期{chinese_weekday}")
        output.append(f"值班人：{on_duty_person}")
        if remarks:
            output.append(f"备注：{remarks}")
    else:
        on_duty_person_id = '无'
        output.append(f"今天的日期：{today_str} 星期{chinese_weekday}")
        output.append("值班人：今天没有排班")

    # 找到未来一周的值班人及其备注
    future_on_duty = df[df['日期'].dt.date.isin(next_week_dates)][['日期', '值班人', '备注']].reset_index(drop=True)

    output.append("\n未来一周的值班人：")
    for index, row in future_on_duty.iterrows():
        weekday = weekdays[row['日期'].weekday()]
        remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
        remark_text = f" 备注：{remark}" if remark else ""
        output.append(f"{row['日期'].strftime('%Y-%m-%d')} 星期{weekday} - {row['值班人']}{remark_text}")

    # 返回结果
    result = {
        "content": "\n".join(output),
        "id": on_duty_person_id
    }

    return result


# 调用函数并获取返回的字典
result = get_duty_info()
print(result)