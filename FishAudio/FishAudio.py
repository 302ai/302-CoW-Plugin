import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
import time


@plugins.register(name="FishAudio",
                  desc="FishAudio",
                  version="1.0",
                  author="masterke",
                  desire_priority=100)
class FishAudio(Plugin):
    tasks = {}
    # config_data = None
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")

    def on_handle_context(self, e_context: EventContext):
        self.context = e_context['context']
        self.e_context = e_context
        self.channel = e_context['channel']
        self.message = e_context["context"].content
        if self.context.type == ContextType.TEXT:
            if self.message not in ["公开音色", "创建音色", "重置创建音色任务"] and not(self.message.startswith("文生音频")):
                return
        elif self.context.type != ContextType.VOICE:
            return
        elif self.context.kwargs['session_id'] not in self.tasks:
            return
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as file:
            self.config_data = json.load(file)
        print(self.tasks)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        if self.message == "公开音色":
            result, result_type = self.get_public_audio_model()
        if self.message.startswith("文生音频"):
            result, result_type = self.text2audio()
        if self.message == "创建音色":
            result ,result_type = self.creat_audio_model_step1()
        if self.message == "重置创建音色任务":
            result, result_type = self.clear_task()
        if self.context.type == ContextType.VOICE:
            result, result_type = self.creat_audio_model_step2()

        reply = Reply()
        if result != None:
            reply.type = result_type
            reply.content = result
            self.e_context["reply"] = reply
            self.e_context.action = EventAction.BREAK_PASS
        else:
            reply.type = ReplyType.ERROR
            reply.content = "获取失败,等待修复⌛️"
            self.e_context["reply"] = reply
            self.e_context.action = EventAction.BREAK_PASS
    # =======================函数定义部分==========================
    def get_public_audio_model(self):
        url = "https://api.302.ai/fish-audio/model"
        headers = {'Content-Type': 'application/json','Authorization': self.config_data['api_key']}
        try:
            response = requests.request("GET", url, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'items' not in rjson:
                return None, ReplyType.ERROR
            else:
                for item in rjson:
                    public_audio_model = "✅公开模型如下：\n" + "\n\n".join([f"{item['title']}\n{item['_id']}" for item in rjson['items']])
                return public_audio_model, ReplyType.TEXT
        except Exception as e:
            logger.info(f"[{__class__.__name__}] 【公开模型】接口抛出异常{e}")
            return None, ReplyType.ERROR
    def text2audio(self):
        pattern = r"文生音频@[0-9a-zA-Z]+@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, tone_id, prompt= self.message.split("@")
        else:
            return self.get_help_text()
        # ⚠️debug
        # relpy_message = f"✅生成成功！\n\n🆔音色id：738d0cc1a3e9430a9de2b544a466a7fc\n🔗音频链接：https://file.302ai.cn/gpt/imgs/20241017/3f7051830f244c1ebf3920a0a49e60f9.mp3"
        # return relpy_message, ReplyType.TEXT
        url = "https://api.302.ai/fish-audio/v1/tts"
        headers = {'Content-Type': 'application/json','Authorization': self.config_data['api_key']}
        payload = json.dumps({
                            "text": prompt,
                            "reference_id": tone_id,
                            "chunk_length": 200,
                            "normalize": True,
                            "format": "mp3",
                            "mp3_bitrate": 64,
                            "opus_bitrate": 32,
                            "latency": "normal"
                            })
        try:
            response = requests.request("POST", url=url, headers=headers, data=payload)
            rjson = response.json()
            if response.status_code != 200 or 'url' not in rjson:
                return None, ReplyType.ERROR
            else:
                relpy_message = f"✅生成音频成功！\n\n🆔音色id：{tone_id}\n🔗音频链接：{rjson['url']}"
                return relpy_message, ReplyType.TEXT        
        except Exception as e:
            logger.info(f"[{__class__.__name__}] 【文生音频】接口抛出异常{e}")
            return None, ReplyType.ERROR
    def creat_audio_model_step1(self):
        if self.context.kwargs['session_id'] in self.tasks:
            return "您有任务正在处理中，请勿重复提交！使用【重置创建音色任务】命令释放！", ReplyType.ERROR
        else:
            self.tasks[self.context.kwargs['session_id']] = True
            logger.info(f"[{__class__.__name__}] 存入任务列表[{self.context.kwargs['session_id']}->{self.tasks[self.context.kwargs['session_id']]}]")
            return("请按下语音讲话...",ReplyType.INFO)
    def creat_audio_model_step2(self):
        self.context.get("msg").prepare()
        file_path = self.context.content
        file_name = os.path.basename(file_path)
        url = "https://api.302.ai/fish-audio/model"
        payload = {'visibility': 'private',
                    'type': 'tts',
                    'train_mode': 'fast',
                    'title': self.context.kwargs['session_id']}
        headers = {'Authorization': self.config_data['api_key']}
        with open(file_path, 'rb') as f:
            files = [('voices', (file_name, f, 'audio/wav'))]
            try:
                response = requests.post(url=url, headers=headers, data=payload, files=files)
                rjson = response.json()
                if response.status_code != 201 or '_id' not in rjson or 'title' not in rjson:
                    logger.info(f"[{__class__.__name__}] 【创建音色】接口返回错误{response.text}")
                    return None, ReplyType.ERROR
                else:
                    relpy_message = f"✅创建音色成功！\n\n📌音色名称：{rjson['title']}\n🆔音色id：{rjson['_id']}"
                    self.clear_task()
                    return relpy_message, ReplyType.TEXT
            except Exception as e:
                logger.info(f"[{__class__.__name__}] 【创建音色】接口抛出异常{e}")
                return None, ReplyType.ERROR
    def clear_task(self):
        if self.context.kwargs['session_id'] in self.tasks:
            del self.tasks[self.context.kwargs['session_id']]
            return "【创建音色】任务释放成功！", ReplyType.INFO
        else:
            return "您没有【创建音色】任务可以释放！", ReplyType.ERROR
        
    def feedback(self, message, reply_type):
        reply = Reply(reply_type, message)
        self.e_context["channel"].send(reply, self.e_context["context"]) 
    def get_help_text(self, **kwargs):
        help_text = f"""1️⃣【文生音频@音色id@要转音频的文字】使用指定的音色将文本转为音频，例如"文生音频@738d0cc1a3e9430a9de2b544a466a7fc@我是一只快乐的小羊羊"
2️⃣【公开音色】查看当前公开的音色id，例如：雷军，蔡徐坤等
3️⃣【创建音色】快速克隆一个自己的声音
4️⃣【重置创建音色任务】清空创建音色的任务
"""
        return help_text, ReplyType.TEXT