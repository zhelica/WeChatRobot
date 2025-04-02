# -*- coding: utf-8 -*-
import json

import requests
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
from base.zhiban.zhiban import DutyScheduler
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
        self.prohibitedWords = self.config.prohibitedWords
        self.command = self.config.command
        self.command_format = self.config.command_format
        self.zhiban = self.config.zhiban
        self.zhibanMethod = DutyScheduler(self.config)
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
            """以第一人称回答问题，扮演人类，与人类正常交流，而不只是刻板的回答问题，日常交流要简介，不要一下子很多字，一大篇文章。群内简介：群里最有钱的是咖总""",
            # "，请用烦人整体画饼的领导的方式来回答"
        ]
        keyWord = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
        song_name = None
        for command in self.command:
            if keyWord.startswith(command):
                # 截取关键词之后的部分作为歌名
                song_name = keyWord[len(command):].strip()
                break
        if not self.chat:  # 没接 ChatGPT，固定回复
            rsp = "你@我干嘛？"
        else:  # 接了 ChatGPT，智能回复
            if msg.content == "天气":
                self.weatherReport()
            elif song_name:
                result = self.handle_music(msg, song_name)  # 确保 handle_music 执行完毕并获取其返回值
                rsp = result
            elif msg.roomid in self.zhiban["enable"]:
                if keyWord.startswith("值班"):
                    # rsp = zhiban.get_duty_info()["content"]
                    rsp = self.zhibanMethod.get_future_duty_by_id(msg.sender)["content"]

                    # if not msg.sender:
                    #     return
                    # ats = ""
                    # ats += f" @{self.wcf.get_alias_in_chatroom(msg.sender, msg.roomid)}"
                    # self.wcf.send_text(f"{ats}\n\n{msg.content}", msg.roomid, msg.sender)
                    #
                elif keyWord.startswith("本月值班"):
                    # rsp = zhiban.get_duty_info()["content"]
                    rsp = self.zhibanMethod.get_monthly_duty_info()["content"]

            elif self.contains_keywords(keyWord):
                #获取群成员
                # room_members = self.wcf.get_chatroom_members(msg.roomid)
                # 提取目标昵称
                # target_nickname = keyWord.replace("踢出去", "").strip()
                #检查列表里面名称为xxx的 {wxid1: 昵称1, wxid2: 昵称2, ...}
                # matched_wxids = self.check_member_by_nickname(room_members, target_nickname)
                isT = self.wcf.del_chatroom_members(msg.roomid,msg.sender)
                if isT==1:
                    rsp="你发表了不当言论，现将你移出群聊✈️\n 欢迎再次进来。\n请大家文明交流，谢谢！"
                    self.wcf.invite_chatroom_members(msg.roomid, msg.sender)
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
                        msg.content = f"{msg.content} {random.choice(styles)}，对方的姓名是，回答问题的时候称呼上对方的姓名{user_name}"
                    else:
                        # 如果不在juan开头且没有名字，只追加随机样式
                        msg.content = f"{msg.content} {random.choice(styles)}，对方的姓名不清楚，不用称呼对方的姓名"
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
                self.LOG.info(f"消息类型========{msg.type}")  # 使用f-string打印信息
                q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
                self.LOG.info(f"问题内容========{q}")  # 使用f-string打印信息
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
            if song_name:
                print("发送--------------------------------"+rsp)
                self.wcf.forward_msg(5342065067458527220,msg.roomid)
                # num = self.wcf.send_xml(msg.roomid, rsp, 3,None)  # 使用 handle_music 返回的结果
                # print(f"返回值============{num}")
            elif msg.from_group():
                self.sendTextMsg(rsp, msg.roomid, msg.sender)
            else:
                self.sendTextMsg(rsp, msg.sender)

            return True
        else:
            self.LOG.error(f"无法从 ChatGPT 获得答案")
            return False

    def contains_keywords(self,sentence: str) -> bool:
        """判断句子中是否包含指定关键词

        Args:
            sentence (str): 要检查的句子
            keywords (list): 关键词列表

        Returns:
            bool: 如果句子中包含任意一个关键词，则返回 True，否则返回 False
        """
        keywords=self.prohibitedWords
        for keyword in keywords:
            if keyword in sentence:
                return True
        return False
    def check_member_by_nickname(self, members_dict: Dict[str, str], target_nickname: str) -> str:
        """检查特定昵称是否存在于成员列表中

        Args:
            members_dict (Dict[str, str]): 群成员列表 {wxid1: 昵称1, wxid2: 昵称2, ...}
            target_nickname (str): 目标昵称

        Returns:
            str: 包含目标昵称的所有成员的wxid列表，多个wxid用逗号隔开
        """
        matched_wxids = [wxid for wxid, nickname in members_dict.items() if nickname == target_nickname]
        return ','.join(matched_wxids)
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
        self.LOG.info(f"消息类型========{msg.type}")  # 使用f-string打印信息
        self.LOG.info(f"消息id========{msg.id}")  # 使用f-string打印信息

        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                return

            if msg.is_at(self.wxid):  # 被@
                self.toAt(msg)

            else:
                # 对于没有@机器人的消息，根据一定概率随机决定是否回复

                # reply_prob = 0.1  # 设置回复的概率，比如20%的几率回复
                #
                # if random.random() < reply_prob:
                #     # 使用与@时相同的回复方法或自定义一个不同的方法
                #
                #     self.replytoAt(msg)  # 或者定义一个新的方法如self.randomReply(msg)
                keyWord = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
                if self.contains_keywords(keyWord):
                    # 获取群成员
                    # room_members = self.wcf.get_chatroom_members(msg.roomid)
                    # 提取目标昵称
                    # target_nickname = keyWord.replace("踢出去", "").strip()
                    # 检查列表里面名称为xxx的 {wxid1: 昵称1, wxid2: 昵称2, ...}
                    # matched_wxids = self.check_member_by_nickname(room_members, target_nickname)
                    isT = self.wcf.del_chatroom_members(msg.roomid, msg.sender)
                    if isT == 1:
                        rsp = "你发表了不当言论，现将你移出群聊✈️\n 欢迎再次进来。\n请大家文明交流，谢谢！"
                        self.wcf.invite_chatroom_members(msg.roomid, msg.sender)
                    else:
                        rsp = "踢出失败"
                    self.sendTextMsg(rsp, msg.roomid, msg.sender)
            return  # 处理完群聊信息，后面就不需要处理了
        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)
        elif msg.type == 34:  # 语音消息
            self.LOG.info(f"消息类型========{msg.type}")  # 使用f-string打印信息
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
            contacts = self.wcf.get_contacts()
            # 打印方法返回内容
            print(contacts)
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
                # self.toChitchat(msg)  # 闲聊

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
    def zhibanReport(self) -> None:
        params = self.zhibanMethod.get_duty_info()
        receivers = params["id"]
        content = params["content"]
        print("content======="+content)
        print("receivers======="+receivers)
        roomid = self.zhiban["enable"][0]
        print("roomid======="+roomid)

        if not receivers:
            return
        ats = ""
        ats += f" @{self.wcf.get_alias_in_chatroom(receivers, roomid)}"
        self.wcf.send_text(f"{ats}\n\n{content}", roomid, receivers)
        # self.wcf.send_text(f"{content}", "26202314469@chatroom", receivers)

        # self.sendTextMsg(content, receivers)
    def weatherReport(self) -> None:
        receivers = self.config.WEATHER
        if not receivers or not self.config.CITY_CODE:
            self.LOG.warning("未配置天气城市代码或接收人")
            return

        report = Weather(self.config.CITY_CODE).get_weather()
        for r in receivers:
            self.sendTextMsg(report, r)
    def handle_music(self, msg: WxMsg,songName:str)-> None:
        # 使用 requests 库进行同步 HTTP 请求
        # response = requests.get(
        #     f"https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?gm={songName}&n=1&br=2&type=json"
        # )
        response = requests.get(f"https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?gm={songName}&n=1&br=2&type=json", timeout=15)
        # data_json = r.json()
        # # 确保请求成功
        # response.raise_for_status()

        # 解析 JSON 数据
        data = response.json()
        # 提取所需信息
        title = data["title"]
        singer = data["singer"]
        url = data["link"]
        music_url = data["music_url"].split("?")[0]
        cover_url = data["cover"]
        lyric = data["lrc"]

        # 构造 XML 字符串
        xml = f"""<?xml version="1.0"?>
<msg>
        <appmsg appid="" sdkver="0">
                <title>弱水三千 (0.8x DJ苏熠鸣)</title>
                <des>苏熠鸣</des>
                <type>3</type>
                <action>view</action>
                <url>https://music.163.com/#/song?id=2614435703</url>
                <lowurl>https://music.163.com/#/song?id=2614435703</lowurl>
                <dataurl>https://m701.music.126.net/20250306175001/49ca92c14e034bfc41b8c54f7f37c339/jdymusic/obj/wo3DlMOGwrbDjj7DisKw/45065516559/9d3c/94da/c911/898b986f8a36d9e184c0a7f9cad60b71.mp3</dataurl>
                <lowdataurl>https://m701.music.126.net/20250306175001/49ca92c14e034bfc41b8c54f7f37c339/jdymusic/obj/wo3DlMOGwrbDjj7DisKw/45065516559/9d3c/94da/c911/898b986f8a36d9e184c0a7f9cad60b71.mp3</lowdataurl>
                <songalbumurl>https://p1.music.126.net/gfhjZuI0aaBgh1ZPyCjZqg==/109951169846003643.jpg</songalbumurl>
                <songlyric>[by:苏熠鸣]
[00:20.397]梨花飘落在你窗前
[00:24.687]画中伊人在闺中怨
[00:29.320]谁把思念轻描淡写
[00:33.445]只想留住时间为你穿越
[00:37.795]我停步白墙青瓦的屋檐
[00:42.389]等你撑伞走过我身边
[00:46.867]古镇上
[00:48.094]谁家的炊烟在为我们酝酿当年的月圆
[00:56.091]—双鸳
[00:58.163]一双鸳鸯戏在雨中那水面
[01:02.726]就像思念苦里透着甜
[01:07.214]我不问弱水三千几人能为我怨
[01:11.661]轮回百转只求陪你续前缘
[01:16.223]一曲悠悠弦断邂逅的古街
[01:20.801]爱的桥段叫我怎么写
[01:25.697]那弱水三千若能把那今生湮灭
[01:29.688]前世亏欠我愿等来生再还
[02:15.674]篆刻离别烟雨江南
[02:20.153]你的美我不忍落款
[02:24.641]牧笛吹皱岁月的脸
[02:28.886]红尘相笑看偏偏为你着恋
[02:33.137]你手绣梅花报春的眉间
[02:37.692]溢满永世不悔的无邪
[02:42.099]牌坊上斑驳的记载
[02:46.734]那是你为等我刻下的誓言
[02:51.271]一双鸳
[02:53.505]一双鸳鸯戏在雨中那水面
[02:57.977]就像思念苦里透着甜
[03:02.533]我不问弱水三千几人能为我怨
[03:07.094]轮回百转只求陪你续前缘
[03:11.623]一曲悠悠弦断邂逅的古街
[03:16.000]爱的桥段叫我怎么写
[03:20.664]那弱水三千若能把那今生湮灭
[03:25.029]前世亏欠我愿等来生再还</songlyric>
                <appattach>
                        <cdnthumbaeskey />
                        <aeskey />
                </appattach>
                <thumburl>https://p1.music.126.net/gfhjZuI0aaBgh1ZPyCjZqg==/109951169846003643.jpg</thumburl>
                <webviewshared>
                        <jsAppId><![CDATA[]]></jsAppId>
                        <publisherReqId><![CDATA[0]]></publisherReqId>
                </webviewshared>
        </appmsg>
        <fromusername>wxid_c0yjh5nyvk3e22</fromusername>
        <scene>0</scene>
        <appinfo>
                <version>1</version>
                <appname></appname>
        </appinfo>
        <commenturl></commenturl>
</msg>
"""
        return xml