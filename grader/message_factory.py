from typing import Dict
from grader.interfaces import MessageFactory


class OpenAIMessageFactory(MessageFactory):
    """OpenAI消息创建工厂实现
    
    创建符合OpenAI API格式的消息对象。
    """
    
    def create_system_message(self, content: str) -> Dict:
        """创建系统消息
        
        Args:
            content: 消息内容
            
        Returns:
            系统消息字典
        """
        return {"role": "system", "content": content}
    
    def create_user_message(self, content: str) -> Dict:
        """创建用户消息
        
        Args:
            content: 消息内容
            
        Returns:
            用户消息字典
        """
        return {"role": "user", "content": content}
    
    def create_image_message(self, image_data: str) -> Dict:
        """创建包含图片的消息
        
        Args:
            image_data: 图片数据（Base64编码）
            
        Returns:
            包含图片的消息字典
        """
        return {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                }
            ]
        }