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
    content: str = None
    # config_data = None
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")

    def get_help_text(self, **kwargs):
        help_text = f"发送【绘图 提示词】"
        return help_text

    def on_handle_context(self, e_context: EventContext):
        # 只处理文本消息
        if e_context['context'].type != ContextType.TEXT:
            return
        
        self.content = e_context["context"].content.strip()
        if self.content.startswith("绘图"):
            channel = e_context["channel"]
            logger.info(f"[{__class__.__name__}] 收到消息: {self.content}")
            reply = Reply(ReplyType.TEXT, "🎨正在飞速生成中 预计需要10秒...")
            channel.send(reply, e_context["context"]) 
            # 读取配置文件
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as file:
                    self.config_data = json.load(file)
            else:
                logger.error(f"[{__class__.__name__}] 请先配置{config_path}文件")
                return

            reply = Reply()
            result = self.fluxpro()
            if result != None:
                reply.type = ReplyType.IMAGE_URL
                reply.content = result
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            else:
                reply.type = ReplyType.ERROR
                reply.content = "获取失败,等待修复⌛️"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

    def fluxpro(self):
        # 用户在关键词后添加了空格
        if self.content.startswith("绘图 "):
            self.content = self.content[3:]
        # 用户在关键词后没有添加空格
        elif self.content.startswith("绘图"):
            self.content = self.content[2:]
            
        logger.info(f"[{__class__.__name__}] 中文提示词为:{self.content}")
        
        # 将中文提示词转换为英文提示词
        try:
            url = "https://api.302.ai/v1/chat/completions"

            payload = json.dumps({
            "model": "deepl-en",
            "message": f"{self.content}"
            })
            headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.config_data['api_key']}"
            }
            response = requests.post(url=url, data=payload, headers=headers)
            if response.status_code == 200:
                rjson = response.json()
                logger.info(f"[{__class__.__name__}] 翻译接口获取成功,英文提示词为{rjson['output']}")
                self.content = rjson['output']
            else:
                logger.info(f"[{__class__.__name__}] 翻译接口请求失败:{response.status_code}")
                raise requests.ConnectionError
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 翻译接口抛出异常:{e}")
            
        # 编码提示词
        self.content = quote(self.content)
        
        # 获取图片
        try:
            url = "https://api.302.ai/302/submit/flux-pro-v1.1"
            payload = json.dumps({
                                    "prompt": f"{self.content}",
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
            if response.status_code == 200:
                rjson = response.json()
                img_url = rjson["images"][0]["url"]
                logger.info(f"[{__class__.__name__}] 获取成功，图片链接为{img_url}")
                return img_url
            else:
                logger.error(f"请求失败:{response.status_code}")
                raise requests.ConnectionError
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 接口抛出异常:{e}")
        return None
