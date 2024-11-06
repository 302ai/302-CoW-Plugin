import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger

@plugins.register(name="knowledge_base_chat",
                  desc="Chat（知识库对话）",
                  version="1.0",
                  author="masterke",
                  desire_priority=200)
class knowledge_base_chat(Plugin):
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
        result, result_type = self.knowledge_base_chat()
        
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
    def knowledge_base_chat(self):
        try:
            url = "https://api.302.ai/302/kb/chat/knowledge_base_chat"
            payload = json.dumps({
            "model_name": self.config_data['model_name'],
            "query": self.message,
            "stream": False
            })
            headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {self.config_data['api_key']}",
            'User-Agent': 'https://api.302.ai',
            'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and rjson['code'] == 0:
                logger.info(f"[{__class__.__name__}] 知识库接口获取成功{rjson['data']['answer']}")
                return rjson['data']['answer'], ReplyType.TEXT
            else:
                logger.info(f"[{__class__.__name__}] 知识库接口请求失败:{response.status_code}")
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 知识库接口抛出异常:{e}")
            return None, ReplyType.ERROR
    def get_help_text(self, **kwargs):
        help_text = f"请在【https://dash.302.ai/robots-market/knowledge-base】配置您的知识库机器人，并填入对应机器人集成按钮中的api_key"
        return help_text