import json

# 定义输入和输出文件路径
input_file_path = 'E:/project/pyProject/WeChatRobot/base/file/1.json'
output_file_path = 'E:/project/pyProject/WeChatRobot/base/file/processed_chat_records.json'

# 读取本地JSON文件
with open(input_file_path, 'r', encoding='utf-8') as file:
    chat_records = json.load(file)

# 初始化变量
processed_records = []
buffer_content = ""
last_talker = None

for record in chat_records:
    current_talker = "assistant" if record['talker'] == "wxid_293wbap7cjzw22" else "user"

    # 如果当前发言者与上一条记录的 talker 相同，则追加内容到缓冲区
    if last_talker and record['talker'] == last_talker:
        buffer_content += "\n" + record['msg']
    else:
        # 如果缓冲区有内容，先将之前的内容添加到 processed_records
        if buffer_content:
            processed_records.append(
                {"role": "assistant" if last_talker == "wxid_293wbap7cjzw22" else "user", "content": buffer_content})
        # 更新缓冲区内容
        buffer_content = record['msg']
        # 更新最后的 talker
        last_talker = record['talker']

# 不要忘记添加最后一个条目
if buffer_content:
    processed_records.append(
        {"role": "assistant" if last_talker == "wxid_293wbap7cjzw22" else "user", "content": buffer_content})

# 确保 processed_records 中不会出现连续的 user 或 assistant
final_processed_records = []
for record in processed_records:
    if final_processed_records and final_processed_records[-1]['role'] == record['role']:
        # 如果当前角色与上一条记录的角色相同，则覆盖上一条记录
        final_processed_records[-1]['content'] = record['content']
    else:
        # 否则，直接添加到最终结果中
        final_processed_records.append(record)

# 将处理后的聊天记录写入新的JSON文件
with open(output_file_path, 'w', encoding='utf-8') as file:
    json.dump(final_processed_records, file, ensure_ascii=False, indent=4)

print(f"Processed chat records have been saved to {output_file_path}")