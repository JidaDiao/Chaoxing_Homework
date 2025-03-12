from typing import Optional
from grader.interfaces import ImageProcessor
import requests
from io import BytesIO
import base64
from PIL import Image
import logging


class DefaultImageProcessor(ImageProcessor):
    """默认图片处理器实现
    
    处理图片下载和转换为Base64编码。
    """
    
    def download_image(self, url: str) -> Optional[str]:
        """下载图片并转换为Base64编码
        
        Args:
            url: 图片URL
            
        Returns:
            Base64编码的图片数据，如果下载失败则返回None
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Referer': url  # 添加来源页面，部分网站需要
        }
        try:
            logging.info(f'处理图片: {url}')
            if url.startswith("data:image/"):  # 判断是否是 Base64 图片
                # 处理 Base64 数据
                base64_data = url.split(",")[1]
                return base64_data
            else:
                # 下载图片
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    image_bytes = BytesIO(response.content)
                    image = Image.open(image_bytes)
                    
                    # 确保图片模式为 RGB（JPEG 不支持 RGBA 模式）
                    if image.mode in ("RGBA", "P"):
                        image = image.convert("RGB")
                    
                    # 调整图片大小以减小文件大小
                    width, height = image.size
                    aspect_ratio = max(width, height) / min(width, height)
                    
                    if aspect_ratio > 0.5:
                        # 将短边固定为256，长边按比例缩放
                        if width < height:
                            new_width = 256
                            new_height = int(height * (new_width / width))
                        else:
                            new_height = 256
                            new_width = int(width * (new_height / height))
                    else:
                        # 将长边固定为512，短边按比例缩放
                        if width > height:
                            new_width = 512
                            new_height = int(height * (new_width / width))
                        else:
                            new_height = 512
                            new_width = int(width * (new_height / height))
                    
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 压缩图片并转换为 Base64 格式
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG", quality=80)
                    compressed_image_bytes = buffered.getvalue()
                    
                    return base64.b64encode(compressed_image_bytes).decode('utf-8')
                else:
                    logging.error(f"请求失败，状态码: {response.status_code}")
                    return None
        except Exception as e:
            logging.error(f'下载图片时发生错误: {str(e)}')
            return None