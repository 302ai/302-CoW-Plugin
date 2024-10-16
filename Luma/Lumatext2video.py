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
    # config_data = None
    tasks={}
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")

    def on_handle_context(self, e_context: EventContext):
        # 文本或者图片
        if e_context['context'].type == ContextType.TEXT or e_context['context'].type == ContextType.IMAGE:
            # 文本类型
            if e_context['context'].type == ContextType.TEXT:
                # 插件要处理的文本
                self.content = e_context['context'].content
                self.e_context = e_context
                if self.content.startswith("文生视频") or self.content.startswith("图生视频") or self.content.startswith("查询视频") or self.content=="清空视频任务":
                    logger.info(f"[{__class__.__name__}] 收到消息")
                    # 检查配置文件
                    config_path = os.path.join(os.path.dirname(__file__), "config.json")
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as file:
                            self.config_data = json.load(file)
                    else:
                        logger.error(f"[{__class__.__name__}] 请先配置{config_path}文件")
                        return
                    # 文生视频
                    if self.content=="清空视频任务":
                        # 删除任务列表(存在才删,多次查询不删除)
                        if self.e_context['context'].kwargs['session_id'] in self.tasks:
                            logger.info(f"[{__class__.__name__}] 删除{self.e_context['context'].kwargs['session_id']}的任务")
                            del(self.tasks[self.e_context['context'].kwargs['session_id']])
                        reply = Reply()
                        reply.type = ReplyType.TEXT
                        reply.content = "已清空！"
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        
                    if self.content.startswith("文生视频"):
                        result = self.text2video()
                        reply = Reply()
                        if result != None:
                            reply.type = ReplyType.TEXT
                            reply.content = result
                            e_context["reply"] = reply
                            e_context.action = EventAction.BREAK_PASS
                        else:
                            reply.type = ReplyType.ERROR
                            reply.content = "获取失败,等待修复⌛️"
                            e_context["reply"] = reply
                            e_context.action = EventAction.BREAK_PASS
                            
                    # 图生视频
                    if self.content.startswith("图生视频"):
                        result = self.image2video_step1()
                        reply = Reply()
                        if result != None:
                            reply.type = ReplyType.TEXT
                            reply.content = result
                            e_context["reply"] = reply
                            e_context.action = EventAction.BREAK_PASS
                        else:
                            reply.type = ReplyType.ERROR
                            reply.content = "获取失败,等待修复⌛️"
                            e_context["reply"] = reply
                            e_context.action = EventAction.BREAK_PASS
                    # 查询视频
                    if self.content.startswith("查询视频"):
                        result = self.query_video()
                        reply = Reply()
                        if result != None:
                            if result.startswith("http"):
                                reply = Reply(ReplyType.TEXT, f"您的任务处理完成，正在发送中...⌛️")
                                channel = e_context["channel"]
                                channel.send(reply, e_context["context"]) 
                                # 删除任务列表(存在才删,多次查询不删除)
                                if self.e_context['context'].kwargs['session_id'] in self.tasks:
                                    logger.info(f"[{__class__.__name__}] 删除{self.e_context['context'].kwargs['session_id']}的任务")
                                    del(self.tasks[self.e_context['context'].kwargs['session_id']])
                                reply.type = ReplyType.VIDEO_URL
                                reply.content = result
                                e_context["reply"] = reply
                                e_context.action = EventAction.BREAK_PASS
                            else:
                                reply.type = ReplyType.TEXT
                                reply.content = result
                                e_context["reply"] = reply
                                e_context.action = EventAction.BREAK_PASS
                        else:
                            reply.type = ReplyType.ERROR
                            reply.content = "获取失败,等待修复⌛️"
                            e_context["reply"] = reply
                            e_context.action = EventAction.BREAK_PASS
            # 图片类型
            if e_context['context'].type == ContextType.IMAGE:
                # 插件不处理的图片
                if self.e_context['context'].kwargs['session_id'] not in self.tasks:
                    return
                logger.info(f"[{__class__.__name__}] 收到图片")
                self.content = e_context['context'].content
                self.e_context = e_context
                result = self.image2video_step2()
                reply = Reply()
                if result != None:
                    reply.type = ReplyType.TEXT
                    reply.content = result
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                else:
                    reply.type = ReplyType.ERROR
                    reply.content = "获取失败,等待修复⌛️"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                

    def translate(self, chinese_text: str):
        # 将中文提示词转换为英文提示词
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
            if response.status_code == 200:
                rjson = response.json()
                logger.info(f"[{__class__.__name__}] 翻译接口获取成功,英文提示词为{rjson['output']}")
                return rjson['output']
            else:
                logger.info(f"[{__class__.__name__}] 翻译接口请求失败:{response.status_code}")
                raise requests.ConnectionError
                return None
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 翻译接口抛出异常:{e}")
            return None
            
    def text2video(self):
        if self.content == "文生视频":
            return "请输入【文生视频 一个猫在笼子里】"
        elif self.content.startswith("文生视频 "):
            self.content = self.content[5:]
        elif self.content.startswith("文生视频"):
            self.content = self.content[4:]

        logger.info(f"[{__class__.__name__}] 中文提示词为:{self.content}")
        translated_user_promot = self.translate(self.content)
        if translated_user_promot == None:
            logger.info(f"翻译接口挂了")
            return None
        video_id = self.get_video_url(user_prompt=translated_user_promot)
        message = f"""🎉任务创建成功！\n============\n🆔任务id：{video_id}\n🔍发送【查询视频 id】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待..."""
        return message

    def image2video_step1(self):
        if self.content == "图生视频":
            return "请输入【图生视频 一个猫在大街上】，然后按照提示输入第一帧图片"
        elif self.content.startswith("图生视频 "):
            self.content = self.content[5:]
        elif self.content.startswith("图生视频"):
            self.content = self.content[4:]
        if self.e_context['context'].kwargs['session_id'] in self.tasks:
            return "✖您有任务正在处理中，请勿重复提交！通过查询已生成视频或使用【清空视频任务】命令释放！"
        else:
            self.tasks[self.e_context['context'].kwargs['session_id']] = self.content
            logger.info(f"[{__class__.__name__}] 存入任务列表[{self.e_context['context'].kwargs['session_id']}->{self.tasks[self.e_context['context'].kwargs['session_id']]}]")
            return "请发送图片..."
    def image2video_step2(self):
        self.e_context['context'].get("msg").prepare()
        file_path = self.e_context['context'].content
        translated_user_promot = self.translate(self.tasks[self.e_context['context'].kwargs['session_id']])
        if translated_user_promot == None:
            logger.info(f"翻译接口挂了")
            return None
        print(f"传入的用户名是{self.e_context['context'].kwargs['session_id']},提示词是{translated_user_promot}")
        video_id = self.get_video_url(user_prompt=translated_user_promot, file_path=file_path)
        if video_id == None:
            return None
        message = f"""🎉任务创建成功！\n============\n🆔任务id：{video_id}\n🔍发送【查询视频 id】进行查询\n\n您的作品将在1分钟左右完成，请耐心等待..."""
        return message
        
    def get_video_url(self,user_prompt=None,file_path=None):
        # 获取视频
        # try:
        url = "https://api.302.ai/luma/submit"
        if file_path != None:
            file_name = os.path.basename(file_path)
            print(file_name,file_path)
            headers = {'Authorization': f"Bearer {self.config_data['api_key']}"}
            payload = {'user_prompt': user_prompt}
            with open(file_path, 'rb') as file:
                files = [('image_url', (file_name, file, 'image/png'))]
                response = requests.post(url, headers=headers, data=payload, files=files)
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "图生视频创建成功"
            # response = requests.request("POST", url, headers=headers, data=payload, files=files)
        else:
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "文生视频创建成功"
            headers = {'Authorization': f"Bearer {self.config_data['api_key']}",'Content-Type': 'application/json'}
            payload = json.dumps({'user_prompt': f"{user_prompt}"})
            response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            rjson = response.json()
            video_id = rjson.get('id',None)
            logger.info(f"[{__class__.__name__}] 获取成功，视频id为{video_id}")
            return video_id
        else:
            logger.error(f"请求失败:{response.status_code}")
            raise requests.ConnectionError
            return None
        # except Exception as e:
        #     logger.error(f"[{__class__.__name__}] 接口抛出异常:{e}")
        #     return None
    
    def query_video(self):
        # 查询视频函数
        if self.content == "查询视频":
            return "请输入【查询视频 xxxxxxx】"
        elif self.content.startswith("查询视频 "):
            id = self.content[5:]
        elif self.content.startswith("查询视频"):
            id = self.content[4:]
        try:
            # # ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            # return "https://cdn.jsdelivr.net/gh/MasterKe2003/my_blog_picture/2024%2F10%2F16%2F1729066148.mp4"
            url = f"https://api.302.ai/luma/task/{id}/fetch"
            headers = {
                'Authorization': f"Bearer {self.config_data['api_key']}",
                'Content-Type': 'application/json'
            }
            payload = json.dumps({})
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.status_code == 200:
                rjson = response.json()
                state = rjson["state"]
                if state == "pending":
                    message=f"您的任务{id}正在处理中，请耐心等待...⌛️"
                    logger.info(f"[{__class__.__name__}] {message}")
                    return message
                elif state == "completed":
                    return rjson["video"]
                else:
                    return None
            else:
                logger.error(f"请求失败:{response.status_code}")
                raise requests.ConnectionError
                return None
        except Exception as e:
            logger.error(f"[{__class__.__name__}] 接口抛出异常:{e}")
            return None
    
    def get_help_text(self, **kwargs):
        help_text = (
            f"➊[文生视频 提示词]：根据文字生成视频。\n➋[图生视频 提示词]：根据文字和图片生成视频。\n➌[查询视频 luma_xxxxxxxxxx]：在创建任务后您将获得一个任务id，使用此唯一任务id获取您的结果。\n"
        )
        return help_text