import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger


@plugins.register(name="midjourney",
                  desc="https://doc.302.ai/api-160578876",
                  version="1.0",
                  author="masterke",
                  desire_priority=100)
class midjourney(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")
    def on_handle_context(self, e_context: EventContext):
        self.context = e_context['context']
        self.e_context = e_context
        self.channel = e_context['channel']
        self.message = e_context["context"].content
        if self.context.type != ContextType.TEXT:
            return
        elif not(self.message.startswith("mj")):
            return
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as file:
            self.config_data = json.load(file)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        if self.message.startswith("mj画"):
            result, result_type = self.midjourney_Imagine()
        elif self.message.startswith("mj查询"):
            result, result_type = self.midjourney_Fetch()
        elif self.message.startswith("mj放大"):
            result, result_type = self.midjourney_Action_upsample()
        elif self.message.startswith("mj类似"):
            result, result_type = self.midjourney_Action_variation()
        elif self.message.startswith("mj重画"):
            result, result_type = self.midjourney_Action_reroll()  
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
    def midjourney_Imagine(self):
        pattern = r"mj画@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text()
        try:
            url = "https://api.302.ai/mj/submit/imagine"
            payload = json.dumps({
                                    "prompt": f"{prompt}",
                                })
            headers = {
                'mj-api-secret': self.config_data['api_key'],
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and rjson.get("code") in [1, 22] and 'result' in rjson:
                return f"🎉任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n💡提示词：{prompt}\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
            else:
                logger.info(f"[{__class__.__name__}] midjourney_Imagine返回错误{response.text}")
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] midjourney_Imagine抛出异常:{e}")
            return None, ReplyType.ERROR
    def midjourney_Fetch(self):
        pattern = r"mj查询@\d{16}$"
        match = re.search(pattern, self.message)
        if match:
            keyword, id = self.message.split("@")
        else:
            return self.get_help_text()
        try:
            url = f"https://api.302.ai/mj/task/{id}/fetch"
            payload = json.dumps({})
            headers = {
                'mj-api-secret': self.config_data['api_key'],
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.get(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and 'status' in rjson:
                if rjson['status'] == "SUCCESS" and rjson.get("imageUrl") != None:
                    if rjson['action'] in ['IMAGINE', 'VARIATION', 'REROLL']:
                        self.feedback(f"{rjson['imageUrl']}", ReplyType.IMAGE_URL)
                        return f"🎉任务已完成！\n============\n🆔任务id：{id}\n\n♻️发送【mj重画@{id}】重新生成4张照片\n🔍发送【mj放大@{id}@1】放大某张图片\n🧩发送【mj类似@{id}@1】生成4张与某张图片类似图片", ReplyType.TEXT
                    elif rjson['action'] == 'UPSCALE':
                        self.feedback(f"{rjson['imageUrl']}", ReplyType.IMAGE_URL)
                        return f"🎉任务已完成！\n============\n🆔任务id：{id}", ReplyType.TEXT
                    else:
                        return None, ReplyType.ERROR
                else:
                    message=f"⌛️您的任务{id}正在处理中，请耐心等待..."
                    return message, ReplyType.INFO
            else:
                logger.info(f"[{__class__.__name__}] midjourney_Fetch返回错误{response.text}")
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] midjourney_Fetch抛出异常:{e}")
            return None, ReplyType.ERROR
    def midjourney_Action_upsample(self):
        pattern = r"mj放大@\d{16}@[1-4]$"
        match = re.search(pattern, self.message)
        if match:
            keyword, id, num = self.message.split("@")
        else:
            return self.get_help_text()
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸请确保id任务类型不是放大！", ReplyType.ERROR
        for i in button:
            if i['label'] == f"U{num}":
                cmd = i['customId']
        try:
            url = f"https://api.302.ai/mj/submit/action"
            payload = json.dumps({
                    "customId": cmd,
                    "taskId": id})
            headers = {
                'mj-api-secret': self.config_data['api_key'],
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and (rjson['code']!= 1 or rjson['code']!= 22) and 'result' in rjson:
                return f"🎉任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
            else:
                logger.info(f"[{__class__.__name__}] midjourney_Action_upsample返回错误{response.text}")
                return None, ReplyType.ERROR    
        except Exception as e:  
            logger.error(f"[{__class__.__name__}] midjourney_Action_upsample抛出异常:{e}")
            return None, ReplyType.ERROR
    def midjourney_Action_variation(self):
        pattern = r"mj类似@\d{16}@[1-4]$"
        match = re.search(pattern, self.message)
        if match:
            keyword, id, num = self.message.split("@")
        else:
            return self.get_help_text()
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸请确保id任务类型不是放大！", ReplyType.ERROR
        for i in button:
            if i['label'] == f"V{num}":
                cmd = i['customId']
        try:
            url = f"https://api.302.ai/mj/submit/action"
            payload = json.dumps({
                    "customId": cmd,
                    "taskId": id})
            headers = {
                'mj-api-secret': self.config_data['api_key'],
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and (rjson['code']!= 1 or rjson['code']!= 22) and 'result' in rjson:
                return f"🎉任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
            else:
                logger.info(f"[{__class__.__name__}] midjourney_Action_variation返回错误{response.text}")
                return None, ReplyType.ERROR    
        except Exception as e:  
            logger.error(f"[{__class__.__name__}] midjourney_Action_variation抛出异常:{e}")
            return None, ReplyType.ERROR
    def midjourney_Action_reroll(self):
        pattern = r"mj重画@\d{16}$"
        match = re.search(pattern, self.message)
        if match:
            keyword, id = self.message.split("@")
        else:
            return self.get_help_text()
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸请确保id任务类型不是放大！", ReplyType.ERROR
        for i in button:
            if i['customId'].startswith("MJ::JOB::reroll::0::"):
                cmd = i['customId']
        try:
            url = f"https://api.302.ai/mj/submit/action"
            payload = json.dumps({
                    "customId": cmd,
                    "taskId": id})
            headers = {
                'mj-api-secret': self.config_data['api_key'],
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and (rjson['code']!= 1 or rjson['code']!= 22) and 'result' in rjson:
                return f"🎉任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
            else:
                logger.info(f"[{__class__.__name__}] midjourney_Action_variation返回错误{response.text}")
                return None, ReplyType.ERROR    
        except Exception as e:  
            logger.error(f"[{__class__.__name__}] midjourney_Action_variation抛出异常:{e}")
            return None, ReplyType.ERROR
    def midjourney_get_buttons(self, id):
        try:
            url = f"https://api.302.ai/mj/task/{id}/fetch"
            payload = json.dumps({})
            headers = {
                'mj-api-secret': self.config_data['api_key'],
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.get(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and 'status' in rjson:
                if rjson['status'] == "SUCCESS" and rjson.get("imageUrl") != None:
                    if rjson['action'] in ['IMAGINE', 'UPSCALE', 'VARIATION', 'REROLL']:
                        return rjson['buttons']
                    else:
                        return None
        except Exception as e:
            logger.error(f"[{__class__.__name__}] midjourney_get_buttons抛出异常:{e}")
            return None
    def feedback(self, message, reply_type):
        reply = Reply(reply_type, message)
        self.e_context["channel"].send(reply, self.e_context["context"]) 
    def get_help_text(self, **kwargs):
        help_text = f"【mj画@提示词】通过文本生成图片，例如【mj画@一只猪在天上飞】\n【mj查询@任务id】查询任务状态，例如【mj查询@xxxxxx】\n【mj放大@任务id@图片序号】放大图片，例如【mj放大@xxxxx@1】\n【mj类似@任务id@图片序号】生成4张类似图片，例如【mj类似@xxxxx@1】\n【mj重画@任务id】重画4张图片，例如【mj重画@xxxxx】"
        return help_text, ReplyType.INFO