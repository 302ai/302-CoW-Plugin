import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from urllib.parse import quote


@plugins.register(name="302AI_T2P",
                  desc="图片生成",
                  version="1.1",
                  author="masterke",
                  desire_priority=100)
class T2P(Plugin):
    model = {}
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
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as file:
            self.config_data = json.load(file)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        if self.message.startswith("绘图"):
            if self.context.kwargs['session_id'] not in self.model:
                self.model[self.context.kwargs['session_id']] = "fluxpro_v10"
                
            if self.model[self.context.kwargs['session_id']] == "fluxpro_v10":
                result, result_type = self.fluxpro_v10()
            elif self.model[self.context.kwargs['session_id']] == "fluxpro_v11":
                result, result_type = self.fluxpro_v11()
            elif self.model[self.context.kwargs['session_id']] == "fluxultra_v11":
                result, result_type = self.fluxultra_v11()
            elif self.model[self.context.kwargs['session_id']] == "fluxdev":
                result, result_type = self.fluxdev()
            elif self.model[self.context.kwargs['session_id']] == "fluxschnell":
                result, result_type = self.fluxschnell()
            elif self.model[self.context.kwargs['session_id']] == "midjourney":
                result, result_type = self.midjourney_Imagine()
            elif self.model[self.context.kwargs['session_id']] == "ideogram":
                result, result_type = self.ideogram()
            elif self.model[self.context.kwargs['session_id']] == "recraft":
                result, result_type = self.recraft()

            else:
                result, result_type = self.get_help_text(), ReplyType.ERROR
        elif self.message.startswith("mj查询"):
            result, result_type = self.midjourney_Fetch()
        elif self.message.startswith("mj放大"):
            result, result_type = self.midjourney_Action_upsample()
        elif self.message.startswith("mj类似"):
            result, result_type = self.midjourney_Action_variation()
        elif self.message.startswith("mj重画"):
            result, result_type = self.midjourney_Action_reroll() 
        elif self.message.startswith("切换绘图模型"):
            result, result_type = self.switch_model()
        else:
            return
        
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
    def switch_model(self):
        pattern = r"切换绘图模型@.*"
        match = re.search(pattern, self.message)
        if match:
            model_lists = [ "fluxpro_v10",
                            "fluxpro_v11",
                            "fluxultra_v11",
                            "fluxdev",
                            "fluxschnell",
                            "midjourney",
                            "ideogram",
                            "recraft"]
            keyword, switch_model = self.message.split("@")
            if switch_model in model_lists:
                self.model[self.context.kwargs['session_id']] = switch_model
                return f"切换成功，当前模型为：{self.model[self.context.kwargs['session_id']]}", ReplyType.INFO
            else:
                return "不支持的绘图模型", ReplyType.ERROR
        else:
            return self.get_help_text(), ReplyType.ERROR
        
    # recraft
    def recraft(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️recraft正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/recraft-v3"
            payload = json.dumps({
                                "prompt": translated_prompt,
                                "image_size": {
                                    "width": 1024,
                                    "height": 1024
                                }
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] ideogram接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] ideogram接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # ideogram
    def ideogram(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️ideogram正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/ideogram/generate"
            payload = json.dumps({
                                    "image_request": {
                                        "prompt": translated_prompt
                                    }
                                    })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'data' not in rjson:
                logger.info(f"[{__class__.__name__}] ideogram接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["data"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] ideogram接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # translate
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
       # fluxpro_v11
    # fluxpro_v10
    def fluxpro_v10(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️fluxpro_v10正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-pro"
            payload = json.dumps({
                                    "prompt": f"{translated_prompt}",
                                    "image_size": {
                                        "width": 1024,
                                        "height": 1024
                                    }
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] fluxpro_v10接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxpro_v10接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # fluxpro_v11
    def fluxpro_v11(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️fluxpro_v11正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-pro-v1.1"
            payload = json.dumps({
                                    "prompt": f"{translated_prompt}",
                                    "image_size": {
                                        "width": 1024,
                                        "height": 1024
                                    }
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] fluxpro_v11接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxpro_v11接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # fluxultra_v11
    def fluxultra_v11(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️fluxultra_v11正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-v1.1-ultra"
            payload = json.dumps({
                                    "prompt": f"{translated_prompt}",
                                    "raw": True,
                                    "aspect_ratio": "16:9"
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] fluxultra_v11接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxultra_v11接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # fluxdev
    def fluxdev(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️fluxdev正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-dev"
            payload = json.dumps({
                                    "prompt": f"{translated_prompt}",
                                    "image_size": {
                                        "width": 1024,
                                        "height": 1024
                                    }
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] fluxdev接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxdev接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # fluxschnell
    def fluxschnell(self):
        pattern = r"绘图@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text(), ReplyType.ERROR
        self.feedback(f"⌛️fluxschnell正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-dev"
            payload = json.dumps({
                                    "prompt": f"{translated_prompt}",
                                    "image_size": {
                                        "width": 1024,
                                        "height": 1024
                                    }
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] fluxschnell接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxschnell接口抛出异常:{e}")
            return None, ReplyType.ERROR
    # midjourney
    def midjourney_Imagine(self):
        pattern = r"绘图@.*"
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
                return f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n💡提示词：{prompt}\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
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
            return self.get_help_text(), ReplyType.ERROR
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
                        return f"🎉任务已完成！\n🆔任务id：{id}\n============\n\n♻️发送【mj重画@{id}】重新生成4张照片\n🔍发送【mj放大@{id}@1】放大某张图片\n🧩发送【mj类似@{id}@1】生成4张与某张图片类似图片", ReplyType.TEXT
                    elif rjson['action'] == 'UPSCALE':
                        self.feedback(f"{rjson['imageUrl']}", ReplyType.IMAGE_URL)
                        return f"🎉任务已完成！\n🆔任务id：{id}", ReplyType.TEXT
                    else:
                        return None, ReplyType.ERROR
                elif rjson['status'] == "FAILURE":
                    message = f"❌任务失败！\n🆔任务id：{id}\n============\n\n💡失败原因：{rjson['failReason']}"
                    return message, ReplyType.INFO
                elif rjson['status'] in ['SUBMITTED', 'IN_PROGRESS']:
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
            return self.get_help_text(), ReplyType.ERROR
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸当前任务id类型已经是放大，无法再放大！", ReplyType.ERROR
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
                return f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
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
            return self.get_help_text(), ReplyType.ERROR
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸当前任务id类型已经是放大，无法再放大！", ReplyType.ERROR
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
                return f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
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
            return self.get_help_text(), ReplyType.ERROR
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸当前任务id类型已经是放大，无法再放大！", ReplyType.ERROR
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
                return f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询@{rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...", ReplyType.TEXT
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
            print(rjson)
            if response.status_code == 200 and 'status' in rjson:
                if rjson['status'] == "SUCCESS" and rjson.get("imageUrl") != None:
                    if rjson['action'] in ['IMAGINE', 'VARIATION', 'REROLL']:
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
        help_text = f"指令：【切换绘图模型@模型名】\n例如：【切换绘图模型@midjourney】\n目前可用模型有：fluxpro_v10（默认）、midjourney、ideogram、recraft\n更多信息查看：https://blog.masterke.cn/posts/T2P_Image_Generation/"
        return help_text