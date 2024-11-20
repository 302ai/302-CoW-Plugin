import re
import time
import requests
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from urllib.parse import quote


@plugins.register(
    name="302AI_T2P",
    desc="图片生成",
    version="1.2",
    author="masterke",
    desire_priority=100,
)
class T2P(Plugin):
    model = {}

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
        # 绘图指令
        if self.message.startswith("绘图"):
            prompt = (
                self.message[3:]
                if self.message.startswith("绘图 ")
                else self.message[2:]
            )
            # 判断当前用户的模型
            if self.context.kwargs["session_id"] not in self.model:
                self.model[self.context.kwargs["session_id"]] = "fluxpro_v10"

            if self.model[self.context.kwargs["session_id"]] == "fluxpro_v10":
                result, result_type = self.fluxpro_v10(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "fluxpro_v11":
                result, result_type = self.fluxpro_v11(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "fluxultra_v11":
                result, result_type = self.fluxultra_v11(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "fluxdev":
                result, result_type = self.fluxdev(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "fluxschnell":
                result, result_type = self.fluxschnell(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "midjourney":
                result, result_type = self.midjourney_Imagine(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "ideogram":
                result, result_type = self.ideogram(prompt)
            elif self.model[self.context.kwargs["session_id"]] == "recraft":
                result, result_type = self.recraft(prompt)
            else:
                result, result_type = self.get_help_text(), ReplyType.ERROR
        elif self.message.startswith("切换绘图模型"):
            model = (
                self.message[7:]
                if self.message.startswith("切换绘图模型 ")
                else self.message[6:]
            )
            result, result_type = self.switch_model(model)
        # mj绘图操作
        elif self.message.startswith("mj查询"):
            id = (
                self.message[5:]
                if self.message.startswith("mj查询 ")
                else self.message[4:]
            )
            result, result_type = self.midjourney_Fetch(id)
        elif self.message.startswith("mj放大"):
            pattern = r"mj放大\s\d{16}\s[1-4]$"
            match = re.search(pattern, self.message)
            if match:
                keyword, id, num = self.message.split(" ")
            else:
                return self.get_help_text(), ReplyType.ERROR
            result, result_type = self.midjourney_Action_upsample(id, num)
        elif self.message.startswith("mj类似"):
            pattern = r"mj类似\s\d{16}\s[1-4]$"
            match = re.search(pattern, self.message)
            if match:
                keyword, id, num = self.message.split(" ")
            else:
                return self.get_help_text(), ReplyType.ERROR
            result, result_type = self.midjourney_Action_variation(id, num)
        elif self.message.startswith("mj重画"):
            id = (
                self.message[5:]
                if self.message.startswith("mj重画 ")
                else self.message[4:]
            )
            result, result_type = self.midjourney_Action_reroll(id)
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
    def switch_model(self, model):
        model_lists = self.config_data["model_lists"]
        if model in model_lists:
            self.model[self.context.kwargs["session_id"]] = model
            return (
                f"切换成功，当前模型为：{self.model[self.context.kwargs['session_id']]}",
                ReplyType.INFO,
            )
        elif model == "":
            return self.get_help_text(), ReplyType.INFO
        else:
            return "切换失败，不支持的绘图模型", ReplyType.ERROR

    # recraft
    def recraft(self, prompt):
        self.feedback(
            f"⌛️recraft正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/recraft-v3"
            payload = json.dumps(
                {
                    "prompt": translated_prompt,
                    "image_size": {"width": 1024, "height": 1024},
                }
            )
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "images" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] ideogram接口返回错误{response.text}"
                )
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] ideogram接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # ideogram
    def ideogram(self, prompt):
        self.feedback(
            f"⌛️ideogram正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/ideogram/generate"
            payload = json.dumps({"image_request": {"prompt": translated_prompt}})
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "data" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] ideogram接口返回错误{response.text}"
                )
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
            payload = json.dumps({"model": "deepl-en", "message": f"{chinese_text}"})
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config_data['api_key']}",
            }
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "hello"
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "output" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] 翻译接口请求失败:{response.status_code}"
                )
                return None, ReplyType.ERROR
            else:
                logger.info(
                    f"[{__class__.__name__}] 翻译接口获取成功,英文提示词为{rjson['output']}"
                )
                return rjson["output"]
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 翻译接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # fluxpro_v10
    def fluxpro_v10(self, prompt):
        self.feedback(
            f"⌛️fluxpro_v10正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-pro"
            payload = json.dumps(
                {
                    "prompt": f"{translated_prompt}",
                    "image_size": {"width": 1024, "height": 1024},
                }
            )
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "images" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] fluxpro_v10接口返回错误{response.text}"
                )
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxpro_v10接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # fluxpro_v11
    def fluxpro_v11(self, prompt):
        self.feedback(
            f"⌛️fluxpro_v11正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-pro-v1.1"
            payload = json.dumps(
                {
                    "prompt": f"{translated_prompt}",
                    "image_size": {"width": 1024, "height": 1024},
                }
            )
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "images" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] fluxpro_v11接口返回错误{response.text}"
                )
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxpro_v11接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # fluxultra_v11
    def fluxultra_v11(self, prompt):
        self.feedback(
            f"⌛️fluxultra_v11正在生成图片，请稍等...\n💡提示词：{prompt}",
            ReplyType.INFO,
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-v1.1-ultra"
            payload = json.dumps(
                {"prompt": f"{translated_prompt}", "raw": True, "aspect_ratio": "16:9"}
            )
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "images" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] fluxultra_v11接口返回错误{response.text}"
                )
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxultra_v11接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # fluxdev
    def fluxdev(self, prompt):
        self.feedback(
            f"⌛️fluxdev正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-dev"
            payload = json.dumps(
                {
                    "prompt": f"{translated_prompt}",
                    "image_size": {"width": 1024, "height": 1024},
                }
            )
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "images" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] fluxdev接口返回错误{response.text}"
                )
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxdev接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # fluxschnell
    def fluxschnell(self, prompt):
        self.feedback(
            f"⌛️fluxschnell正在生成图片，请稍等...\n💡提示词：{prompt}", ReplyType.INFO
        )
        translated_prompt = self.translate(prompt)
        try:
            url = "https://api.302.ai/302/submit/flux-dev"
            payload = json.dumps(
                {
                    "prompt": f"{translated_prompt}",
                    "image_size": {"width": 1024, "height": 1024},
                }
            )
            headers = {
                "Authorization": f"Bearer {self.config_data['api_key']}",
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code != 200 or "images" not in rjson:
                logger.info(
                    f"[{__class__.__name__}] fluxschnell接口返回错误{response.text}"
                )
                return None, ReplyType.ERROR
            else:
                return rjson["images"][0]["url"], ReplyType.IMAGE_URL
        except Exception as e:
            logger.error(f"[{__class__.__name__}] fluxschnell接口抛出异常:{e}")
            return None, ReplyType.ERROR

    # midjourney
    def midjourney_Imagine(self, prompt):
        try:
            url = "https://api.302.ai/mj/submit/imagine"
            payload = json.dumps(
                {
                    "prompt": f"{prompt}",
                }
            )
            headers = {
                "mj-api-secret": self.config_data["api_key"],
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if (
                response.status_code == 200
                and rjson.get("code") in [1, 22]
                and "result" in rjson
            ):
                self.feedback(
                    f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍如果一分钟后没有结果，请发送【mj查询 {rjson['result']}】进行查询\n💡提示词：{prompt}\n\n您的作品将在1分钟左右完成，请耐心等待...",
                    ReplyType.TEXT,
                )
                for i in range(6):
                    time.sleep(10)
                    result, result_type = self.midjourney_Fetch(rjson["result"], flag=True)
                    if result != None:
                        return result, result_type

            else:
                logger.info(
                    f"[{__class__.__name__}] midjourney_Imagine返回错误{response.text}"
                )
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] midjourney_Imagine抛出异常:{e}")
            return None, ReplyType.ERROR

    def midjourney_Fetch(self, id, flag=False):
        try:
            url = f"https://api.302.ai/mj/task/{id}/fetch"
            payload = json.dumps({})
            headers = {
                "mj-api-secret": self.config_data["api_key"],
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.get(url=url, data=payload, headers=headers)
            rjson = response.json()
            if response.status_code == 200 and "status" in rjson:
                if rjson["status"] == "SUCCESS" and rjson.get("imageUrl") != None:
                    if rjson["action"] in ["IMAGINE", "VARIATION", "REROLL"]:
                        self.feedback(f"{rjson['imageUrl']}", ReplyType.IMAGE_URL)
                        return (
                            f"🎉任务已完成！\n🆔任务id：{id}\n============\n\n♻️发送【mj重画 {id}】重新生成4张照片\n🔍发送【mj放大 {id} 1】放大某张图片\n🧩发送【mj类似 {id} 1】生成4张与某张图片类似图片",
                            ReplyType.TEXT,
                        )
                    elif rjson["action"] == "UPSCALE":
                        self.feedback(f"{rjson['imageUrl']}", ReplyType.IMAGE_URL)
                        return f"🎉任务已完成！\n🆔任务id：{id}", ReplyType.TEXT
                    else:
                        return None, ReplyType.ERROR
                elif rjson["status"] == "FAILURE":
                    message = f"❌任务失败！\n🆔任务id：{id}\n============\n\n💡失败原因：{rjson['failReason']}"
                    return message, ReplyType.INFO
                elif rjson["status"] in ["SUBMITTED", "IN_PROGRESS"]:
                    message = f"⌛️您的任务{id}正在处理中，请耐心等待..."
                    if flag:
                        return None, ReplyType.ERROR
                    return message, ReplyType.INFO
            else:
                logger.info(
                    f"[{__class__.__name__}] midjourney_Fetch返回错误{response.text}"
                )
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(f"[{__class__.__name__}] midjourney_Fetch抛出异常:{e}")
            return None, ReplyType.ERROR

    def midjourney_Action_upsample(self, id, num):
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸当前任务id类型已经是放大，无法再放大！", ReplyType.ERROR
        for i in button:
            if i["label"] == f"U{num}":
                cmd = i["customId"]
        try:
            url = f"https://api.302.ai/mj/submit/action"
            payload = json.dumps({"customId": cmd, "taskId": id})
            headers = {
                "mj-api-secret": self.config_data["api_key"],
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if (
                response.status_code == 200
                and (rjson["code"] != 1 or rjson["code"] != 22)
                and "result" in rjson
            ):
                return (
                    f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询 {rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...",
                    ReplyType.TEXT,
                )
            else:
                logger.info(
                    f"[{__class__.__name__}] midjourney_Action_upsample返回错误{response.text}"
                )
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(
                f"[{__class__.__name__}] midjourney_Action_upsample抛出异常:{e}"
            )
            return None, ReplyType.ERROR

    def midjourney_Action_variation(self, id, num):
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸当前任务id类型不支持此操作！", ReplyType.ERROR
        for i in button:
            if i["label"] == f"V{num}":
                cmd = i["customId"]
        try:
            url = f"https://api.302.ai/mj/submit/action"
            payload = json.dumps({"customId": cmd, "taskId": id})
            headers = {
                "mj-api-secret": self.config_data["api_key"],
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if (
                response.status_code == 200
                and (rjson["code"] != 1 or rjson["code"] != 22)
                and "result" in rjson
            ):
                return (
                    f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询 {rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...",
                    ReplyType.TEXT,
                )
            else:
                logger.info(
                    f"[{__class__.__name__}] midjourney_Action_variation返回错误{response.text}"
                )
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(
                f"[{__class__.__name__}] midjourney_Action_variation抛出异常:{e}"
            )
            return None, ReplyType.ERROR

    def midjourney_Action_reroll(self, id):
        button = self.midjourney_get_buttons(id)
        if button == None:
            return "🫸当前任务id类型不支持此操作！", ReplyType.ERROR
        for i in button:
            if i["customId"].startswith("MJ::JOB::reroll::0::"):
                cmd = i["customId"]
        try:
            url = f"https://api.302.ai/mj/submit/action"
            payload = json.dumps({"customId": cmd, "taskId": id})
            headers = {
                "mj-api-secret": self.config_data["api_key"],
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.post(url=url, data=payload, headers=headers)
            rjson = response.json()
            if (
                response.status_code == 200
                and (rjson["code"] != 1 or rjson["code"] != 22)
                and "result" in rjson
            ):
                return (
                    f"🎉midjourney任务创建成功！\n============\n🆔任务id：{rjson['result']}\n🔍发送【mj查询 {rjson['result']}】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待...",
                    ReplyType.TEXT,
                )
            else:
                logger.info(
                    f"[{__class__.__name__}] midjourney_Action_variation返回错误{response.text}"
                )
                return None, ReplyType.ERROR
        except Exception as e:
            logger.error(
                f"[{__class__.__name__}] midjourney_Action_variation抛出异常:{e}"
            )
            return None, ReplyType.ERROR

    def midjourney_get_buttons(self, id):
        try:
            url = f"https://api.302.ai/mj/task/{id}/fetch"
            payload = json.dumps({})
            headers = {
                "mj-api-secret": self.config_data["api_key"],
                "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
                "Content-Type": "application/json",
            }
            response = requests.get(url=url, data=payload, headers=headers)
            rjson = response.json()
            print(rjson)
            if response.status_code == 200 and "status" in rjson:
                if rjson["status"] == "SUCCESS" and rjson.get("imageUrl") != None:
                    if rjson["action"] in ["IMAGINE", "VARIATION", "REROLL"]:
                        return rjson["buttons"]
                    else:
                        return None
        except Exception as e:
            logger.error(f"[{__class__.__name__}] midjourney_get_buttons抛出异常:{e}")
            return None

    def feedback(self, message, reply_type):
        reply = Reply(reply_type, message)
        self.e_context["channel"].send(reply, self.e_context["context"])

    def get_help_text(self, **kwargs):
        help_text = f"指令：【切换绘图模型 模型名】\n例如：【切换绘图模型 midjourney】\n目前可用模型有：fluxpro_v10（默认）、midjourney、ideogram、recraft、fluxpro_v11、fluxultra_v11、fluxdev、fluxschnell"
        return help_text
