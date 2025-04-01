import base64


def file_to_base64(file_path):
    """
    读取指定路径的文件，并将其内容编码为Base64字符串。

    :param file_path: 文件的路径
    :return: 文件内容的Base64编码字符串
    """
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
            base64_encoded_data = base64.b64encode(file_content)
            return base64_encoded_data.decode('utf-8')
    except FileNotFoundError:
        print(f"文件未找到：{file_path}")
        return None
    except Exception as e:
        print(f"发生错误：{str(e)}")
        return None


def write_base64_to_file(base64_string, output_file_path):
    """
    将Base64编码的字符串写入到指定的输出文件中。

    :param base64_string: Base64编码的字符串
    :param output_file_path: 输出文件的路径
    """
    try:
        with open(output_file_path, 'w') as file:
            file.write(base64_string)
        print(f"Base64数据已成功写入到 {output_file_path}")
    except Exception as e:
        print(f"写入文件时发生错误：{str(e)}")


# 使用示例
input_file_path = 'C:/Users/李哲/Desktop/processed_chat_records.txt'  # 替换为您的文件路径
output_file_path = 'C:/Users/李哲/Desktop/base.txt'  # 替换为您想要保存Base64内容的文件路径

encoded_string = file_to_base64(input_file_path)

if encoded_string is not None:
    write_base64_to_file(encoded_string, output_file_path)