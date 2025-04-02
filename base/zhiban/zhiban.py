import pandas as pd
from datetime import datetime, timedelta
from configuration import Config
import os
class DutyScheduler:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.people = self.config.zhiban['people']
    def get_duty_info(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建目标文件的路径
        file_path = os.path.join(script_dir, "值班表.xlsx")
        # 创建值班人和ID的映射字典
        person_id_map = self.people

        # 读取Excel文件，并确保日期列被解析为datetime
        df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

        # 获取今天的日期和未来一周的日期范围
        today = datetime.today()
        next_week_dates = [(today + timedelta(days=i)).date() for i in range(1, 8)]  # 转换为仅日期

        # 找到今天的值班信息
        today_str = today.strftime('%Y年%m月%d日')
        today_info = df[df['日期'].dt.date == today.date()]  # 比较时不考虑时间部分

        # 将星期几转换为汉字
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        chinese_weekday = weekdays[today.weekday()]

        output = []
        on_duty_person = ""
        remarks = ""
        if not today_info.empty:
            on_duty_person = today_info.iloc[0]['值班人']
            on_duty_person_id = person_id_map.get(on_duty_person, '未知')  # 获取值班人的ID，如果没有则默认为'未知'
            remarks_raw = today_info.iloc[0]['备注']
            remarks = remarks_raw if isinstance(remarks_raw, str) and '接口值班' in remarks_raw else ''
            output.append(f"日期：{today_str} 星期{chinese_weekday}")
            output.append(f"值班人：{on_duty_person}")
            if remarks:
                output.append(f"备注：{remarks}")
        else:
            on_duty_person_id = '无'
            output.append(f"今天的日期：{today_str} 星期{chinese_weekday}")
            output.append("值班人：今天没有排班")

        # 找到未来一周的值班人及其备注
        future_on_duty = df[df['日期'].dt.date.isin(next_week_dates)][['日期', '值班人', '备注']].reset_index(drop=True)

        output.append("\n未来一周值班：")
        for index, row in future_on_duty.iterrows():
            weekday = weekdays[row['日期'].weekday()]
            remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
            remark_text = f" 备注：{remark}" if remark else ""
            output.append(f"{row['日期'].strftime('%Y年%m月%d日')} 星期{weekday} - {row['值班人']}{remark_text}")

        # 返回结果
        result = {
            "content": "\n".join(output),
            "id": on_duty_person_id,
            "name": on_duty_person,
            "remarks": remarks,
            "date": today.strftime('%Y年%m月%d日')
        }

        return result


    # 新增：通过人员ID查询未来值班的方法
    def get_future_duty_by_id(self,person_id):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建目标文件的路径
        file_path = os.path.join(script_dir, "值班表.xlsx")
        person_id_map = self.people

        # 反转字典，以便通过ID查找姓名
        name_person_map = {v: k for k, v in person_id_map.items()}

        df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

        today = datetime.today()
        future_dates = [(today + timedelta(days=i)).date() for i in range(1, 365)]  # 查找一年内的所有日期

        # 过滤出未来日期的值班信息
        future_df = df[df['日期'].dt.date.isin(future_dates)]

        # 根据传入的ID找到对应的姓名
        person_name = name_person_map.get(person_id, None)
        if not person_name:
            return {"content": f"未找到ID为{person_id}的人员", "duty_info": []}

        # 找到该人员在未来的值班信息
        duty_info = future_df[future_df['值班人'] == person_name]

        output = []
        for index, row in duty_info.iterrows():
            weekday = ["一", "二", "三", "四", "五", "六", "日"][row['日期'].weekday()]
            remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
            remark_text = f" 备注：{remark}" if remark else ""
            output.append(f"{row['日期'].strftime('%Y年%m月%d日')} 星期{weekday} - {row['值班人']}{remark_text}")

        result = {
            "content": f"{person_name} 本月剩余值班信息如下：\n" + "\n".join(
                output) if output else "没有找到相关的值班信息。",
            "duty_info": output
        }

        return result


    # 新增：查询本月全部值班信息的方法
    def get_monthly_duty_info(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建目标文件的路径
        file_path = os.path.join(script_dir, "值班表.xlsx")

        df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

        today = datetime.today()
        start_of_month = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        # 获取本月所有日期
        this_month_dates = pd.date_range(start=start_of_month, end=next_month - timedelta(days=1)).date

        # 过滤出本月的值班信息
        monthly_df = df[df['日期'].dt.date.isin(this_month_dates)]

        output = []
        for index, row in monthly_df.iterrows():
            weekday = ["一", "二", "三", "四", "五", "六", "日"][row['日期'].weekday()]
            remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
            remark_text = f" 备注：{remark}" if remark else ""
            output.append(f"{row['日期'].strftime('%Y年%m月%d日')} 星期{weekday} - {row['值班人']}{remark_text}")

        result = {
            "content": "本月全部值班信息如下：\n" + "\n".join(output) if output else "没有找到相关的值班信息。",
            "duty_info": output
        }

        return result
