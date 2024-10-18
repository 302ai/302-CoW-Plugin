import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from urllib.parse import quote


@plugins.register(name="fluxpro",
                  desc="Flux-Pro（图片生成v1.1）",
                  version="1.0",
                  author="masterke",
                  desire_priority=100)
class fluxpro(Plugin):
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
        elif not(self.message.startswith("文生图片")):
            return
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, 'r') as file:
            self.config_data = json.load(file)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        result, result_type = self.fluxpro()
        
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
    def fluxpro(self):
        pattern = r"文生图片@.*"
        match = re.search(pattern, self.message)
        if match:
            keyword, prompt = self.message.split("@")
        else:
            return self.get_help_text()
        self.feedback(f"⌛️正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO)
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-pro-v1.1"
            payload = json.dumps({
                                    "prompt": f"{translated_prompt}",
                                    "image_size": {
                                        "width": 1024,
                                        "height": 1024
                                    },
                                    "num_inference_steps": 28,
                                    "guidance_scale": 3.5
                                })
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or 'images' not in rjson:
                logger.info(f"[{__class__.__name__}] 文生图片接口返回错误{response.text}")
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 文生图片接口抛出异常:{e}")
            return None, ReplyType.ERROR
    def feedback(self, message, reply_type):
        reply = Reply(reply_type, message)
        self.e_context["channel"].send(reply, self.e_context["context"]) 
    def get_help_text(self, **kwargs):
        help_text = f"【文生图片@提示词】通过文本生成图片，例如【文生图片@一只猪在天上飞】"
        return help_text, ReplyType.INFO