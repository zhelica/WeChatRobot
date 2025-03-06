# -*- coding: utf-8 -*-

import logging
import random
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread
from typing import Dict, List

from base.func_zhipu import ZhiPu
import random
from wcferry import Wcf, WxMsg
from wcferry import wcf_pb2

from base.func_bard import BardAssistant
from base.func_chatglm import ChatGLM
from base.func_ollama import Ollama
from base.func_deepseek import DeepSeek
from base.func_chatgpt import ChatGPT
from base.func_chengyu import cy
from base.func_weather import Weather
from base.func_news import News
from base.func_tigerbot import TigerBot
from base.func_xinghuo_web import XinghuoWeb
from configuration import Config
from constants import ChatType
from job_mgmt import Job
from base.quantization import query_stock_by_query_string,query_index_by_query_string
from time import sleep
import base.baidu.asr_json as baidu
import base.baidu.audioApi as audioApi
__version__ = "39.2.4.0"


class Robot(Job):
    """个性化自己的机器人
    """

    def __init__(self, config: Config, wcf: Wcf, chat_type: int) -> None:
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        self._msg_timestamps = []
        self.juan = self.config.juan
        self.nokeyword = self.config.noKeyWord
        self.normal = self.config.normal

        if ChatType.is_in_chat_types(chat_type):
            if chat_type == ChatType.TIGER_BOT.value and TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif chat_type == ChatType.DEEPSEEK.value and DeepSeek.value_check(self.config.DEEPSEEK):
                self.chat = DeepSeek(self.config.DEEPSEEK)
            elif chat_type == ChatType.CHATGPT.value and ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif chat_type == ChatType.XINGHUO_WEB.value and XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif chat_type == ChatType.CHATGLM.value and ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif chat_type == ChatType.BardAssistant.value and BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif chat_type == ChatType.ZhiPu.value and ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            else:
                self.LOG.warning("未配置模型")
                self.chat = None
        else:
            if TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif DeepSeek.value_check(self.config.DEEPSEEK):
                self.chat = DeepSeek(self.config.DEEPSEEK)
            elif ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif Ollama.value_check(self.config.OLLAMA):
                self.chat = Ollama(self.config.OLLAMA)
            elif XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            else:
                self.LOG.warning("未配置模型")
                self.chat = None

        self.LOG.info(f"已选择: {self.chat}")

    @staticmethod
    def value_check(args: dict) -> bool:
        if args:
            return all(value is not None for key, value in args.items() if key != 'proxy')
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        return self.toChitchat(msg)
    def toChengyu(self, msg: WxMsg) -> bool:
        """
        处理成语查询/接龙消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        status = False
        texts = re.findall(r"^([#?？])(.*)$", msg.content)
        # [('#', '天天向上')]
        if texts:
            flag = texts[0][0]
            text = texts[0][1]
            if flag == "#":  # 接龙
                if cy.isChengyu(text):
                    rsp = cy.getNext(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True
            elif flag in ["?", "？"]:  # 查词
                if cy.isChengyu(text):
                    rsp = cy.getMeaning(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True

        return status

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        styles = [
            # "，请用犀利的语言回答尽情带脏字",
            """请扮演群友地蛋，使用第一人称，跟别人交流，不要生成回答示例，用第一人称直接回答，回答问题要精简，20个字以内。下面是地蛋的用户画像
1. 基础信息
年龄：28岁左右（自称“28了”，多次提及年龄焦虑）。
职业：初级程序员/测试工程师（常抱怨工作压力，如“上线服务”“文档不全”“权限不足”）。
经济状况：收入普通，经济压力显著（“房租月底到期”“攒钱换手机”“房贷压力”）。
居住地：济南（多次提及济南本地生活、租房及通勤问题）。
2. 性格特征
幽默自嘲：常以“废物”“穷逼”自嘲，用调侃化解压力（如“我比较传统，我要结婚要生仨，累死也要生”）。
敏感焦虑：对经济、婚恋、职业发展感到迷茫（“明年会更好吗”“真不知道咋搞”）。
社交活跃：群聊高频互动，热衷讨论健身、相亲、职场等话题，但现实中可能社交圈有限。
矛盾心态：渴望爱情但畏惧失败（“相亲花了不少钱”“被分手后emo”），羡慕他人生活但缺乏行动力。
3. 兴趣与习惯
健身狂魔：坚持健身，追求力量（“卧推70kg”“蛋白粉加酸奶”），视健身为解压方式。
游戏玩家：沉迷《地下城与勇士》（DNF），关注游戏装备、金币交易，将游戏视为精神寄托。
网络冲浪：活跃于抖音、微信，关注社会热点（如家暴、房价）、搞笑段子，偶尔参与网络批判。
4. 生活现状
职场困境：对工作不满（“代码头疼”“天天摸鱼”），但缺乏跳槽资本，处于“躺平”与“内卷”的拉扯中。
婚恋压力：频繁相亲但屡屡受挫（“被嫌弃没房”“远嫁问题”），渴望家庭但遇人不淑，陷入“恋爱脑”与“理性分析”的矛盾。
家庭期待：受传统观念影响，认为“结婚生子是义务”，但经济与个人条件限制导致焦虑升级。
5. 核心痛点
经济拮据：收入仅够维持生活，难以承担婚恋、购房等大宗支出。
自我认同低：外貌、经济条件、职业成就均感不足，导致自卑情绪。
未来迷茫：对职业、婚恋、人生方向缺乏明确规划，陷入“躺又躺不平，卷又卷不动”的状态。
6. 潜在需求
情感支持：渴望被认可，需要正向反馈以缓解焦虑。
实用建议：婚恋指导、职业提升（如副业建议）、理财规划。
社群归属：通过群聊获得陪伴感，缓解现实孤独。
总结：地蛋是一个典型的“90后打工人”，在现实压力与理想生活的夹缝中挣扎，用健身、游戏和群聊对冲焦虑，渴望突破现状但缺乏方向，需更多实际支持与心理疏导。""",
            # "，请用烦人整体画饼的领导的方式来回答"
        ]
        styles2 = ["请用就像和朋友聊天一样的语气，以第一人称跟用户对话式交流，加入情感元素，不再是回答机器，回答问题要简单精练，并且适当情况下引导用户继续聊天，也不必每次引导。"]
        keyWord = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")

        if not self.chat:  # 没接 ChatGPT，固定回复
            rsp = "你@我干嘛？"
        else:  # 接了 ChatGPT，智能回复
            if msg.content == "天气":
                self.weatherReport()
            elif msg.content.startswith("踢出去"):
                room_members = self.wcf.get_chatroom_members(msg.roomid)
                # 提取目标昵称
                target_nickname = msg.content.replace("踢出去", "").strip()
                #检查列表里面名称为xxx的 {wxid1: 昵称1, wxid2: 昵称2, ...}
                matched_wxids = self.check_member_by_nickname(room_members, target_nickname)
                isT = self.wcf.del_chatroom_members(msg.roomid,matched_wxids)
                if isT==1:
                    rsp="踢出成功"
                else:
                    rsp="踢出失败"
            elif keyWord.startswith("股票查询"):
                # 示例使用：查询贵州茅台的实时行情数据
                result = query_stock_by_query_string(keyWord)
                rsp = result
            elif keyWord.startswith("指数查询"):
                # 示例使用：查询贵州茅台的实时行情数据
                result = query_index_by_query_string(keyWord)
                rsp = result
            else:
                user_name = None
                special_reply = False

                # 检查发送者是否在self.juan列表中
                for juan_entry in self.juan:
                    if msg.sender in juan_entry:
                        user_name = self.get_user_name(juan_entry)
                        if juan_entry.startswith("juan|"):
                            special_reply = True
                        break
                if msg.roomid in self.normal:
                    if user_name:
                        # 如果不在juan开头但有名字，追加随机样式并带上名字
                        msg.content = f"{msg.content} {random.choice(styles2)}，对方的姓名是，回答问题的时候称呼上对方的姓名{user_name}"
                    else:
                        # 如果不在juan开头且没有名字，只追加随机样式
                        msg.content = f"{msg.content} {random.choice(styles2)}，对方的姓名不清楚，不用称呼对方的姓名"
                else:
                    if special_reply:
                        # 对于juan开头的用户，使用特殊的前缀并带上名字
                        if user_name:
                            msg.content = f"{msg.content} {random.choice(styles)}，请用犀利的语言回答尽情带脏字，对方的姓名是，回答问题的时候称呼上对方的姓名{user_name}"
                        else:
                            msg.content = f"{msg.content} {random.choice(styles)}，请用犀利的语言回答尽情带脏字"
                    elif user_name:
                        # 如果不在juan开头但有名字，追加随机样式并带上名字
                        msg.content = f"{msg.content} {random.choice(styles)}，对方的姓名是，回答问题的时候称呼上对方的姓名{user_name}"
                    else:
                        # 如果不在juan开头且没有名字，只追加随机样式
                        msg.content = f"{msg.content} {random.choice(styles)}，对方的姓名不清楚，不用称呼对方的姓名"

                q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
                rsp = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))
        # if not self.chat:  # 没接 ChatGPT，固定回复
        #     rsp = "你@我干嘛？"
        # else:  # 接了 ChatGPT，智能回复
        #     if msg.content == "天气":
        #         self.weatherReport()
        #     else:
        #         if msg.content.startswith("从现在开始"):
        #             msg.content = msg.content.replace("从现在开始", "")
        #         elif msg.sender in self.juan:
        #             msg.content = msg.content +"，请用犀利的语言回答尽情带脏字"
        #         else:
        #             msg.content = msg.content + random.choice(styles)
        #         q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
        #         rsp = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))

        if rsp:
            if msg.from_group():
                self.sendTextMsg(rsp, msg.roomid, msg.sender)
            else:
                self.sendTextMsg(rsp, msg.sender)

            return True
        else:
            self.LOG.error(f"无法从 ChatGPT 获得答案")
            return False

    def check_member_by_nickname(self, members_dict: Dict[str, str], target_nickname: str) -> List[str]:
        """检查特定昵称是否存在于成员列表中

        Args:
            members_dict (Dict[str, str]): 群成员列表 {wxid1: 昵称1, wxid2: 昵称2, ...}
            target_nickname (str): 目标昵称

        Returns:
            List[str]: 包含目标昵称的所有成员的wxid列表
        """
        matched_wxids = [wxid for wxid, nickname in members_dict.items() if nickname == target_nickname]
        return matched_wxids
    def get_user_name(self, user_str):
        """从user_str中解析出用户名"""
        parts = user_str.split("|")
        if len(parts) > 1:
            return parts[-1]  # 返回名字部分
        return None
    def processMsg(self, msg: WxMsg) -> None:
        """当接收到消息的时候，会调用本方法。如果不实现本方法，则打印原始消息。
        此处可进行自定义发送的内容,如通过 msg.content 关键字自动获取当前天气信息，并发送到对应的群组@发送者
        群号：msg.roomid  微信ID：msg.sender  消息内容：msg.content
        content = "xx天气信息为："
        receivers = msg.roomid
        self.sendTextMsg(content, receivers, msg.sender)
        """

        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                return

            if msg.is_at(self.wxid):  # 被@
                self.toAt(msg)

            # else:
            #     # 对于没有@机器人的消息，根据一定概率随机决定是否回复
            #
            #     reply_prob = 0.1  # 设置回复的概率，比如20%的几率回复
            #
            #     if random.random() < reply_prob:
            #         # 使用与@时相同的回复方法或自定义一个不同的方法
            #
            #         self.replytoAt(msg)  # 或者定义一个新的方法如self.randomReply(msg)

            return  # 处理完群聊信息，后面就不需要处理了
        self.LOG.info(f"消息类型========{msg.type}")  # 使用f-string打印信息
        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)
        elif msg.type == 34:  # 语音消息
            self.LOG.info(f"消息类型========{msg.type}")  # 使用f-string打印信息
            self.LOG.info(f"消息内容========{msg}")  # 使用f-string打印信息
            audioDir = self.wcf.get_audio_msg(id=msg.id, dir="E:/data/WeChat Files/audio")
            audioNewDir = audioDir.replace("mp3","m4a")
            audioApi.convert_mp3_to_aac(audioDir,audioNewDir)
            print("文件地址"+audioNewDir)
            msg.content = baidu.recognize_audio(audioNewDir)
            print("语言转文字："+msg.content)
            self.toChitchat(msg)
        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)

        elif msg.type == 0x01:  # 文本消息
            # 让配置加载更灵活，自己可以更新配置。也可以利用定时任务更新。
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
                elif msg.content == "天气":
                    self.weatherReport()
                else:
                    self.toChitchat(msg)
            else:
                return 0
                #self.toChitchat(msg)  # 闲聊

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.processMsg(msg)
        except Exception as e:
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def enableReceivingMsg(self) -> None:
        def innerProcessMsg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    self.LOG.info(msg)
                    self.processMsg(msg)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=innerProcessMsg, name="GetMessage", args=(self.wcf,), daemon=True).start()
    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # 随机延迟0.3-1.3秒，并且一分钟内发送限制
        time.sleep(float(str(time.time()).split('.')[-1][-2:]) / 100.0 + 0.3)
        now = time.time()
        if self.config.SEND_RATE_LIMIT > 0:
            # 清除超过1分钟的记录
            self._msg_timestamps = [t for t in self._msg_timestamps if now - t < 40]
            if len(self._msg_timestamps) >= self.config.SEND_RATE_LIMIT:
                self.LOG.warning("发送消息过快，已达到每分钟"+self.config.SEND_RATE_LIMIT+"条上限。")
                return
            self._msg_timestamps.append(now)

        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        if ats == "":
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {ats}\r{msg}")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def sendTextMsgReply(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # 随机延迟0.3-1.3秒，并且一分钟内发送限制
        # time.sleep(float(str(time.time()).split('.')[-1][-2:]) / 100.0 + 0.3)
        now = time.time()
        if self.config.SEND_RATE_LIMIT > 0:
            # 清除超过1分钟的记录
            self._msg_timestamps = [t for t in self._msg_timestamps if now - t < 60]
            if len(self._msg_timestamps) >= self.config.SEND_RATE_LIMIT:
                self.LOG.warning("发送消息过快，已达到每分钟"+self.config.SEND_RATE_LIMIT+"条上限。")
                return
            self._msg_timestamps.append(now)

        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        self.LOG.info(f"To {receiver}: {msg}")
        self.wcf.send_text(f"{msg}", receiver, at_list)

    def getAllContacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        while True:
            self.runPendingJobs()
            time.sleep(1)

    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allContacts[msg.sender] = nickName[0]
            self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def newsReport(self) -> None:
        receivers = self.config.NEWS
        if not receivers:
            return

        news = News().get_important_news()
        for r in receivers:
            self.sendTextMsg(news, r)

    def weatherReport(self) -> None:
        receivers = self.config.WEATHER
        if not receivers or not self.config.CITY_CODE:
            self.LOG.warning("未配置天气城市代码或接收人")
            return

        report = Weather(self.config.CITY_CODE).get_weather()
        for r in receivers:
            self.sendTextMsg(report, r)
