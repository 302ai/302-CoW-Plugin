import re
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger

@plugins.register(name="alias",
                  desc="为godcmd起别名",
                  version="1.0",
                  author="masterke",
                  desire_priority=1000)
class alias(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")
    def on_handle_context(self, e_context: EventContext):
        self.message = e_context["context"].content
        if e_context['context'].type != ContextType.TEXT:
            return
        logger.info(f"[{__class__.__name__}] 收到消息: {e_context['context'].content}")
        # =======================插件处理流程==========================
        if  e_context["context"].content == "#清空对话":
            e_context["context"].content = "#reset"
            e_context.action = EventAction.CONTINUE
        if  e_context["context"].content.startswith("切换对话模型"):
            match_model = (
                self.message[7:]
                if self.message.startswith("切换对话模型 ")
                else self.message[6:]
            )
            if match_model:
                e_context["context"].content = "#model " + match_model
                e_context.action = EventAction.CONTINUE
            else:
                reply = Reply(ReplyType.TEXT, self.get_help_text())
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
        else:
            return
    def get_help_text(self, **kwargs):
        help_text = f"指令：【切换对话模型 模型名】【#清空对话】"
        return help_text