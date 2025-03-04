import json
import logging

class BrowserLogParser:
    @staticmethod
    def parse_url_from_performance_logs(logs, url_pattern, log_message=""):
        """
        从浏览器性能日志中提取包含指定模式的URL
        
        参数:
            logs: 通过driver.get_log('performance')获取的日志列表
            url_pattern: 需要匹配的URL模式字符串
            log_message: 成功时的日志提示信息
        
        返回:
            str: 匹配到的URL或None
        """
        for entry in logs:
            message = json.loads(entry['message'])['message']
            if message.get('method') == 'Network.requestWillBeSent':
                request = message['params']['request']
                if url_pattern in request['url']:
                    if log_message:
                        logging.info(f"{log_message}: {request['url']}")
                    return request['url']
        return None