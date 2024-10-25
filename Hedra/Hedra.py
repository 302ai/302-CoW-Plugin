import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger

@plugins.register(name="Hedra",
                  desc="https://302ai.apifox.cn/api-226162384",
                  version="1.0",
                  author="masterke",
                  desire_priority=100)

class Hedra(Plugin):
    tasks={}
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
            if self.message not in ["口型合成", "重置口型合成任务"] and not(self.message.startswith("查询口型合成视频")):
                return
        else:
            if self.context.type not in [ContextType.IMAGE, ContextType.VOICE]:
                return
            else: 
                if self.context.kwargs['session_id'] not in self.tasks:
                    return
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as file:
            self.config_data = json.load(file)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        if self.context.type == ContextType.TEXT:
            if self.message == "口型合成":
                result, result_type = self.Hedra()
            elif self.message == "重置口型合成任务":
                result, result_type = self.clear_task()
            elif self.message.startswith("查询口型合成视频"):
                result, result_type = self.query_video()
        elif self.context.type == ContextType.IMAGE:
            result, result_type = self.process_image()
        elif self.context.type == ContextType.VOICE:
            result, result_type = self.process_voice()
                 
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
    def Hedra(self):
        params = {
            "image_url": None,
            "voice_url": None
        }
        self.tasks[self.context.kwargs['session_id']] = params
        print(self.tasks)
        return "⌛️请发送图片和语音...", ReplyType.TEXT
    def process_image(self):
        self.context.get("msg").prepare()
        try:
            url = "https://api.302.ai/hedra/api/v1/portrait"
            file_path = self.context.content
            file_name = os.path.basename(file_path)
            headers = {'Authorization': f"Bearer {self.config_data['api_key']}"}
            payload = {}
            with open(file_path, 'rb') as file:
                files = [('file', (file_name, file, 'image/png'))]
                response = requests.post(url, headers=headers, data=payload, files=files)
            rjson = response.json() 
            if response.status_code != 200 or 'url' not in rjson:
                logger.info(f"[{__class__.__name__}] process_image错误：{response.text}")
                return None, ReplyType.ERROR
            else:
                self.tasks[self.context.kwargs['session_id']]['image_url'] = rjson['url']
                if (self.tasks[self.context.kwargs['session_id']]['image_url'] is not None) and (self.tasks[self.context.kwargs['session_id']]['voice_url'] is not None):
                    return self.creat_task()
                else:
                    return "🧩已收到图片，请发送要合成的语音...", ReplyType.INFO
        except Exception as e:
            logger.error(f"[{__class__.__name__}] process_image抛出异常:{e}")
            return None, ReplyType.ERROR
    def process_voice(self):
        self.context.get("msg").prepare()
        try:
            url = "https://api.302.ai/hedra/api/v1/audio"
            headers = {'Authorization': f"Bearer {self.config_data['api_key']}"}
            payload = {}
            file_path = self.context.content
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as file:
                files = [('file', (file_name, file, 'audio/mp3'))]
                response = requests.post(url, headers=headers, data=payload, files=files)
            rjson = response.json() 
            if response.status_code != 200 or 'url' not in rjson:
                logger.info(f"[{__class__.__name__}] process_voice错误：{response.text}")
                return None, ReplyType.ERROR
            else:
                self.tasks[self.context.kwargs['session_id']]['voice_url'] = rjson['url']
                if (self.tasks[self.context.kwargs['session_id']]['image_url'] is not None) and (self.tasks[self.context.kwargs['session_id']]['voice_url'] is not None):
                    return self.creat_task()
                else:
                    return "🎤已收到语音，请发送要合成的人像图片...", ReplyType.INFO
        except Exception as e:
            logger.error(f"[{__class__.__name__}] process_voice抛出异常:{e}")
            return None, ReplyType.ERROR
    def creat_task(self):
        url = "https://api.302.ai/hedra/api/v1/characters"
        payload = json.dumps({"avatarImage": self.tasks[self.context.kwargs['session_id']]['image_url'],"audioSource": "audio","voiceUrl": self.tasks[self.context.kwargs['session_id']]['voice_url']})
        headers = {'Content-Type': 'application/json','Authorization': f"Bearer {self.config_data['api_key']}"}
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                rjson = response.json()
                if rjson.get('jobId'):
                    del self.tasks[self.context.kwargs['session_id']]
                    return f"🎉任务创建成功！\n===============\n\n任务ID：{rjson['jobId']}\n🔍【查询口型合成视频@{rjson['jobId']}】查询您的视频", ReplyType.TEXT
                else:
                    logger.info(f"[{__class__.__name__}] creat_task返回错误：{response.text}")
                    del self.tasks[self.context.kwargs['session_id']]
                    return None, ReplyType.ERROR
            else:
                logger.info(f"[{__class__.__name__}] creat_task请求错误：{response.text}")
                del self.tasks[self.context.kwargs['session_id']]
                return None, ReplyType.ERROR
        except Exception as e:
            logger.info(f"[{__class__.__name__}] creat_task抛出异常：{e}")
            return None, ReplyType.ERROR
    def query_video(self):
        pattern = r"查询口型合成视频@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, id = self.message.split("@")
        else:
            return self.get_help_text()
        try:
            url = f"https://api.302.ai/hedra/api/v1/projects/{id}"
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'Content-Type': 'application/json'
            }
            payload = json.dumps({})
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.status_code == 200:
                rjson = response.json()
                print(rjson)
                if 'status' in rjson:
                    if rjson['status'] == "InProgress":
                        message=f"⌛️您的任务{id}正在处理中，请耐心等待..."
                        logger.info(f"[{__class__.__name__}] {message}")
                        return message, ReplyType.INFO
                    elif rjson['status'] == "Completed":
                        self.feedback("⌛️您的任务处理完成，正在发送中...", ReplyType.INFO)
                        self.clear_task()
                        return rjson["videoUrl"], ReplyType.VIDEO_URL
                    else:
                        return None, ReplyType.ERROR
            else: 
                logger.info(f"[{__class__.__name__}] query_video返回错误：{response.text}")
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] query_video抛出异常:{e}")
            return None, ReplyType.ERROR
        
    def feedback(self, message, reply_type):
        reply = Reply(reply_type, message)
        self.e_context["channel"].send(reply, self.e_context["context"]) 
    def clear_task(self):
        if self.context.kwargs['session_id'] in self.tasks:
            del self.tasks[self.context.kwargs['session_id']]
            return "【口型合成】任务释放成功！", ReplyType.INFO
        else:
            return "您没有【口型合成】任务可以释放！", ReplyType.ERROR
    
    def get_help_text(self, **kwargs):
        help_text = (f"""1️⃣【口型合成】根据提示创建口型合成任务
2️⃣【查询口型合成视频@任务id】在创建口型合成任务后您将获得一个任务id，使用此唯一任务id获取您的结果
3️⃣【重置口型合成任务】重置任务状态重新开始流程
""")
        return help_text, ReplyType.TEXT