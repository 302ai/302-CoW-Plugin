import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger

@plugins.register(name="Lumatext2video",
                  desc="Lumatext2video",
                  version="1.0",
                  author="masterke",
                  desire_priority=100)

class Lumatext2video(Plugin):
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
            if self.message not in ["重置图生视频任务"] and not(self.message.startswith("文生视频") or self.message.startswith("图生视频") or self.message.startswith("查询视频")):
                return
        else:
            if self.context.type != ContextType.IMAGE:
                return
            else:
                if self.context.kwargs['session_id'] not in self.tasks:
                    return
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as file:
            self.config_data = json.load(file)
        print(self.tasks)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        if self.message=="重置图生视频任务":
            result, result_type = self.clear_task() 
        elif self.message.startswith("文生视频"):
            result, result_type = self.text2video()
        elif self.message.startswith("图生视频"):
            result, result_type = self.image2video_step1()
        elif self.message.startswith("查询视频"):
            result, result_type = self.query_video()
        else:
            result, result_type = self.image2video_step2()
                 
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
    def translate(self, chinese_text: str):
        try:
            url = "https://api.302.ai/v1/chat/completions"
            payload = json.dumps({
            "model": "deepl-en",
            "message": f"{chinese_text}"
            })
            headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.config_data['api_key']}"
            }
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "hello"
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'output' not in rjson:
                logger.info(f"[{__class__.__name__}] 翻译接口请求失败:{response.status_code}")
                return None, ReplyType.ERROR
            else:
                logger.info(f"[{__class__.__name__}] 翻译接口获取成功,英文提示词为{rjson['output']}")
                return rjson['output']
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 翻译接口抛出异常:{e}")
            return None, ReplyType.ERROR
    def text2video(self):
        pattern = r"文生视频@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt= self.message.split("@")
        else:
            return self.get_help_text()
        translated_prompt = self.translate(prompt)
        if translated_prompt == None:
            return None, ReplyType.ERROR
        else:
            video_id = self.get_video_url(user_prompt=translated_prompt)
            message = f"""🎉任务创建成功！\n============\n🆔任务id：{video_id}\n🔍发送【查询视频@{video_id}】进行查询\n💡提示词：{translated_prompt}\n\n您的作品将在1分钟左右完成，请耐心等待..."""
            return message, ReplyType.TEXT

    def image2video_step1(self):
        pattern = r"图生视频@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt= self.message.split("@")
        else:
            return self.get_help_text()
        if self.context.kwargs['session_id'] in self.tasks:
            return "您有任务正在处理中，请勿重复提交！使用【重置图生视频任务】命令释放！", ReplyType.ERROR
        else:
            self.tasks[self.context.kwargs['session_id']] = prompt
            logger.info(f"[{__class__.__name__}] 存入任务列表[{self.context.kwargs['session_id']}->{self.tasks[self.context.kwargs['session_id']]}]")
            return("请发送图片...",ReplyType.INFO)
    def image2video_step2(self):
        self.context.get("msg").prepare()
        file_path = self.context.content
        translated_prompt = self.translate(self.tasks[self.context.kwargs['session_id']])
        if translated_prompt == None:
            return None, ReplyType.ERROR
        else:
            video_id = self.get_video_url(user_prompt=translated_prompt, file_path=file_path)
            if video_id == None:
                return None, ReplyType.ERROR
            else:
                message = f"""🎉任务创建成功！\n============\n🆔任务id：{video_id}\n🔍发送【查询视频@{video_id}】进行查询\n💡提示词：{translated_prompt}\n\n您的作品将在1分钟左右完成，请耐心等待..."""
                return message, ReplyType.TEXT
        
    def get_video_url(self,user_prompt=None,file_path=None):
        try:
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "文生视频创建成功"
            url = "https://api.302.ai/luma/submit"
            if file_path != None:
                file_name = os.path.basename(file_path)
                print(file_name,file_path)
                headers = {'Authorization': f"Bearer {self.config_data['api_key']}"}
                payload = {'user_prompt': user_prompt}
                with open(file_path, 'rb') as file:
                    files = [('image_url', (file_name, file, 'image/png'))]
                    response = requests.post(url, headers=headers, data=payload, files=files)
            else:
                headers = {'Authorization': f"Bearer {self.config_data['api_key']}",'Content-Type': 'application/json'}
                payload = json.dumps({'user_prompt': f"{user_prompt}"})
                response = requests.request("POST", url, headers=headers, data=payload)
            rjson = response.json() 
            if response.status_code != 200 or 'id' not in rjson:
                logger.info(f"[{__class__.__name__}] 获取视频接口错误：{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson['id']
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 获取视频接口抛出异常:{e}")
            return None, ReplyType.ERROR
    
    def query_video(self):
        pattern = r"查询视频@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, id = self.message.split("@")
        else:
            return self.get_help_text()
        try:
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "https://cdn.jsdelivr.net/gh/MasterKe2003/my_blog_picture/2024%2F10%2F16%2F1729066148.mp4", ReplyType.VIDEO_URL
            url = f"https://api.302.ai/luma/task/{id}/fetch"
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'Content-Type': 'application/json'
            }
            payload = json.dumps({})
            response = requests.request("GET", url, headers=headers, data=payload)
            rjson = response.json()
            if response.status_code != 200 or 'state' not in rjson or 'video' not in rjson:
                return None, ReplyType.ERROR
            else: 
                if rjson['state'] == "pending":
                    message=f"⌛️您的任务{id}正在处理中，请耐心等待..."
                    logger.info(f"[{__class__.__name__}] {message}")
                    return message, ReplyType.INFO
                elif rjson['state'] == "completed":
                    self.feedback("⌛️您的任务处理完成，正在发送中...", ReplyType.INFO)
                    self.clear_task()
                    return rjson["video"], ReplyType.VIDEO_URL
                else:
                    logger.info(f"[{__class__.__name__}] 接口返回错误：{response.text}")
                    return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 查询视频接口抛出异常:{e}")
            return None, ReplyType.ERROR
        
    def feedback(self, message, reply_type):
        reply = Reply(reply_type, message)
        self.e_context["channel"].send(reply, self.e_context["context"]) 
    def clear_task(self):
        if self.context.kwargs['session_id'] in self.tasks:
            del self.tasks[self.context.kwargs['session_id']]
            return "【图生视频】任务释放成功！", ReplyType.INFO
        else:
            return "您没有【图生视频】任务可以释放！", ReplyType.ERROR
    
    def get_help_text(self, **kwargs):
        help_text = (f"""1️⃣【文生视频@提示词】根据文字生成视频，例如【文生视频@一只猪在天上飞】
2️⃣【图生视频@提示词】根据文字和第一帧图片生成视频
3️⃣【查询视频@任务id】在创建生成视频任务后您将获得一个任务id，使用此唯一任务id获取您的结果
""")
        return help_text, ReplyType.TEXT