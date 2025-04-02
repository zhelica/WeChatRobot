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
        file_path = os.path.join(script_dir, "值班表.xlsx")
        person_id_map = self.people

        df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

        today = datetime.today()
        next_week_dates = [(today + timedelta(days=i)).date() for i in range(1, 8)]

        today_str = f"{today.year}年{today.month}月{today.day}日"
        today_info = df[df['日期'].dt.date == today.date()]

        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        chinese_weekday = weekdays[today.weekday()]

        output = []
        on_duty_person = ""
        remarks = ""
        if not today_info.empty:
            on_duty_person = today_info.iloc[0]['值班人']
            on_duty_person_id = person_id_map.get(on_duty_person, '未知')
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

        future_on_duty = df[df['日期'].dt.date.isin(next_week_dates)][['日期', '值班人', '备注']].reset_index(drop=True)

        output.append("\n未来一周值班：")
        for index, row in future_on_duty.iterrows():
            weekday = weekdays[row['日期'].weekday()]
            remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
            remark_text = f" 备注：{remark}" if remark else ""
            output.append(f"{row['日期'].year}年{row['日期'].month}月{row['日期'].day}日 星期{weekday} - {row['值班人']}{remark_text}")

        result = {
            "content": "\n".join(output),
            "id": on_duty_person_id,
            "name": on_duty_person,
            "remarks": remarks,
            "date": today_str
        }

        return result

    def get_future_duty_by_id(self, person_id):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "值班表.xlsx")
        person_id_map = self.people

        name_person_map = {v: k for k, v in person_id_map.items()}

        df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

        today = datetime.today()
        future_dates = [(today + timedelta(days=i)).date() for i in range(1, 365)]

        future_df = df[df['日期'].dt.date.isin(future_dates)]

        person_name = name_person_map.get(person_id, None)
        if not person_name:
            return {"content": f"未找到ID为{person_id}的人员", "duty_info": []}

        duty_info = future_df[future_df['值班人'] == person_name]

        output = []
        for index, row in duty_info.iterrows():
            weekday = ["一", "二", "三", "四", "五", "六", "日"][row['日期'].weekday()]
            remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
            remark_text = f" 备注：{remark}" if remark else ""
            output.append(f"{row['日期'].year}年{row['日期'].month}月{row['日期'].day}日 星期{weekday} - {row['值班人']}{remark_text}")

        result = {
            "content": f"{person_name} 本月剩余值班信息如下：\n" + "\n".join(
                output) if output else "没有找到相关的值班信息。",
            "duty_info": output
        }

        return result

    def get_monthly_duty_info(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "值班表.xlsx")

        df = pd.read_excel(file_path, header=1, parse_dates=['日期'])

        today = datetime.today()
        start_of_month = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        this_month_dates = pd.date_range(start=start_of_month, end=next_month - timedelta(days=1)).date

        monthly_df = df[df['日期'].dt.date.isin(this_month_dates)]

        output = []
        for index, row in monthly_df.iterrows():
            weekday = ["一", "二", "三", "四", "五", "六", "日"][row['日期'].weekday()]
            remark = row['备注'] if isinstance(row['备注'], str) and '接口值班' in row['备注'] else ''
            remark_text = f" 备注：{remark}" if remark else ""
            output.append(f"{row['日期'].year}年{row['日期'].month}月{row['日期'].day}日 星期{weekday} - {row['值班人']}{remark_text}")

        result = {
            "content": "本月全部值班信息如下：\n" + "\n".join(output) if output else "没有找到相关的值班信息。",
            "duty_info": output
        }

        return result