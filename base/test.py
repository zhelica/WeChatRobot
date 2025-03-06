class Robot:
    def contains_keywords(self, sentence: str, keywords: list) -> bool:
        """判断句子中是否包含指定关键词

        Args:
            sentence (str): 要检查的句子
            keywords (list): 关键词列表

        Returns:
            bool: 如果句子中包含任意一个关键词，则返回 True，否则返回 False
        """
        return any(keyword in sentence for keyword in keywords)

# 示例用法
robot = Robot()
sentence = "今天天气不错，你爹带你妈去公园散步。"
keywords = ["你爹", "你妈"]

# 正确调用方法
if robot.contains_keywords(sentence, keywords):
    print("句子中包含指定关键词")
else:
    print("句子中不包含指定关键词")