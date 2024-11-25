import re
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger

@plugins.register(name="chat_search_302",
                  desc="自动调用pplx模型进行搜索",
                  version="1.0",
                  author="jomy",
                  desire_priority=200)
class chat_search_302(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")

    def on_handle_context(self, e_context: EventContext):
        self.context = e_context["context"]
        self.e_context = e_context
        self.channel = e_context["channel"]
        self.message = e_context["context"].content
        if self.context.type != ContextType.TEXT:
            return
        # =======================读取配置文件==========================
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as file:
            self.config_data = json.load(file)
        logger.info(f"[{__class__.__name__}] 收到消息: {self.message}")
        # =======================插件处理流程==========================
        if self.message.startswith("搜"):
            prompt = (
                self.message[2:]
                if self.message.startswith("搜 ")
                else self.message[1:]
            )
            result, result_type = self.chat_search_302(prompt)
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
    def chat_search_302(self,prompt):
        try:
            url = "https://api.302.ai/v1/chat/completions"
            # Define a default system prompt
            default_system_prompt = ""
            
            # Check if system_prompt is empty, and use default if necessary
            system_prompt = self.config_data.get('system_prompt', '').strip()
            if not system_prompt:
                system_prompt = default_system_prompt

            payload = json.dumps({
                "model": self.config_data['search_model'],
                "messages": [{"role": "user", "content": system_prompt}, {"role": "user", "content": prompt}]
            })
            headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {self.config_data['api_key']}",
            'User-Agent': 'https://api.302.ai',
            'Content-Type': 'application/json'
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200:
                # Extracting the message content
                message_content = rjson['choices'][0]['message']['content']
                
                # Extracting and formatting citations
                citations_list = rjson.get('citations', [])
                formatted_citations = "\n".join([f"[{index + 1}] {url}" for index, url in enumerate(citations_list)])
                
                # Concatenating message content with formatted citations
                combined_output = f"{message_content}\n{formatted_citations}"
                
                logger.info(f"[{__class__.__name__}] 搜索接口获取成功")
                return combined_output, ReplyType.TEXT
            else:
                logger.info(f"[{__class__.__name__}] 搜索接口请求失败:{response.status_code}")
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 搜索接口抛出异常:{e}")
            return None, ReplyType.ERROR
    def get_help_text(self, **kwargs):
        help_text = f"范例：搜 OpenAI"
        return help_text
