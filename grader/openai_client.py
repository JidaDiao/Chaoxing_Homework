import re
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from grader.interface import IOpenAIClient

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("openai").setLevel(logging.ERROR)


class OpenAIClient(IOpenAIClient):
    """OpenAI客户端类，负责与OpenAI API的所有交互

    实现IOpenAIClient接口，提供OpenAI API的封装功能，包括创建聊天完成请求和处理响应。

    Attributes:
        client: OpenAI API客户端实例
    """

    def __init__(self, api_key: str, base_url: str):
        """初始化OpenAI客户端

        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def create_completion(self, model: str, messages: List[Dict[str, Any]]) -> Any:
        """创建聊天完成请求

        Args:
            model: 使用的模型名称
            messages: 消息列表

        Returns:
            API响应对象
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response
        except Exception as e:
            logging.error(f"OpenAI API调用失败: {str(e)}")
            raise

    def extract_json_from_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """从响应内容中提取JSON数据

        使用多种策略从响应中提取和解析JSON格式的内容，提高解析成功率。

        Args:
            response_content: API响应的文本内容

        Returns:
            提取的JSON数据，如果提取失败则返回None
        """
        if not response_content:
            logging.error("响应内容为空")
            return None

        # 预处理响应内容，尝试修复一些常见问题
        response_content = self._preprocess_response(response_content)

        # 策略1: 尝试从Markdown代码块中提取JSON (```json ... ```)
        markdown_json_pattern = r"```(?:json)?\s*\n([\s\S]*?)\n```"
        markdown_matches = re.findall(markdown_json_pattern, response_content)

        for match in markdown_matches:
            try:
                cleaned_match = self._fix_common_json_issues(match.strip())
                json_data = json.loads(cleaned_match)
                logging.info("成功从Markdown代码块中提取JSON")
                return json_data
            except json.JSONDecodeError:
                continue

        # 策略2: 尝试找到最外层的花括号对，避免嵌套JSON问题
        potential_json = self._find_outermost_json(response_content)
        if potential_json:
            try:
                cleaned_json = self._fix_common_json_issues(potential_json)
                json_data = json.loads(cleaned_json)
                logging.info("成功使用括号匹配提取JSON")
                return json_data
            except json.JSONDecodeError:
                pass

        # 策略3: 处理复杂文本内容，尝试多种清理方式
        json_patterns = [
            r'\{[\s\S]*\}',  # 标准花括号
            r'\[[\s\S]*\]'   # 数组格式
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, response_content)
            for match in matches:
                # 尝试多种清洗方法
                cleaning_methods = [
                    lambda x: x,  # 原始内容
                    self._fix_common_json_issues,  # 基本修复
                    self._aggressive_json_fix,     # 激进修复
                    self._handle_nested_quotes     # 处理嵌套引号
                ]
                
                for clean_method in cleaning_methods:
                    try:
                        cleaned_json = clean_method(match)
                        json_data = json.loads(cleaned_json)
                        logging.info(f"成功使用 {clean_method.__name__} 解析JSON")
                        return json_data
                    except (json.JSONDecodeError, AttributeError):
                        continue

        # 策略4: 尝试提取和重建JSON结构
        try:
            reconstructed_json = self._reconstruct_json(response_content)
            if reconstructed_json:
                logging.info("成功使用重建策略获取JSON")
                return reconstructed_json
        except Exception as e:
            logging.error(f"重建JSON失败: {str(e)}")

        # 策略5: 针对特定格式的评分数据处理
        try:
            scoring_data = self._extract_scoring_data(response_content)
            if scoring_data:
                logging.info("成功从评分数据中提取JSON")
                return scoring_data
        except Exception as e:
            logging.error(f"提取评分数据失败: {str(e)}")

        logging.error(f"所有JSON提取方法都失败，原内容: {response_content[:200]}...")
        return None

    def _preprocess_response(self, text: str) -> str:
        """对响应内容进行预处理，修复常见问题"""
        # 移除可能干扰解析的BOM标记和特殊字符
        text = text.strip().replace('\ufeff', '')
        
        # 处理常见标点符号和格式问题
        text = text.replace('，', ',').replace('：', ':').replace('；', ';')
        
        # 移除可能的多余标点
        text = text.rstrip('.。, \t\n\r')
        
        return text

    def _fix_common_json_issues(self, text: str) -> str:
        """修复常见的JSON格式问题"""
        # 替换单引号为双引号（但要注意保护嵌套引号）
        result = ''
        in_quotes = False
        for i, char in enumerate(text):
            if char == "'" and (i == 0 or text[i-1] != '\\'):
                if not in_quotes:
                    result += '"'
                    in_quotes = True
                else:
                    result += '"'
                    in_quotes = False
            else:
                result += char
        text = result
        
        # 处理末尾可能多出的逗号
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        # 处理键没有引号的情况
        text = re.sub(r'(\{|\,)\s*([a-zA-Z0-9_\u4e00-\u9fa5]+):', r'\1"\2":', text)
        
        # 处理多余的括号
        balance = 0
        for char in text:
            if char == '{':
                balance += 1
            elif char == '}':
                balance -= 1
        
        # 如果括号不平衡，尝试修复
        if balance > 0:
            text = text + '}' * balance
        elif balance < 0:
            text = '{' * abs(balance) + text
            
        return text

    def _aggressive_json_fix(self, text: str) -> str:
        """更激进的JSON修复策略，尝试解决复杂格式问题"""
        # 处理嵌套引号
        text = text.replace('\\"', "'").replace('"', '\\"').replace("'", '"')
        
        # 处理特殊字符和转义
        text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        
        # 处理中文字符周围的引号
        text = re.sub(r'(["\'])([\u4e00-\u9fa5]+)(["\'])', r'"\2"', text)
        
        # 更严格地处理键值对格式
        # 匹配键值对并规范化
        pattern = r'[\'"]?([^\'",]+)[\'"]?\s*:\s*([\'"].*?[\'"]|\{.*?\}|\[.*?\]|[^,}\]]+)'
        matches = re.findall(pattern, text)
        if matches:
            new_json = '{'
            for key, value in matches:
                # 清理键
                clean_key = key.strip().replace('"', '').replace("'", '')
                # 清理值
                if value.startswith(('{', '[')) or value.strip().replace('.', '', 1).isdigit():
                    clean_value = value.strip()
                else:
                    # 字符串值需要加双引号
                    value_cleaned = value.strip().replace('"', '').replace("'", '')
                    clean_value = f'"{value_cleaned}"'
                new_json += f'"{clean_key}":{clean_value},'
            new_json = new_json.rstrip(',') + '}'
            return new_json
        
        return text

    def _handle_nested_quotes(self, text: str) -> str:
        """专门处理嵌套引号问题，特别针对评分标准等复杂文本"""
        # 第一步：识别并替换最外层引号
        outer_quote_pattern = r"(['\"]{1})([^'\"]*(?:['\"]{1}.*?['\"]{1})*[^'\"]*)(['\"]{1})"
        
        def replace_nested_quotes(match):
            outer_quote = match.group(1)
            content = match.group(2)
            # 将内部引号替换为交替的引号类型
            if outer_quote == '"':
                content_cleaned = content.replace('"', "'")
                return f'"{content_cleaned}"'
            else:
                content_cleaned = content.replace("'", '"')
                return f'\'{content_cleaned}\''
        
        processed_text = re.sub(outer_quote_pattern, replace_nested_quotes, text)
        
        # 第二步：处理嵌套在对象值中的引号
        # 先识别对象的键值对
        key_value_pattern = r'"([^"]+)"\s*:\s*(.+?)(?=,\s*"|\s*\})'
        
        def process_value(match):
            key = match.group(1)
            value = match.group(2).strip()
            
            # 如果值包含嵌套引号，尝试转义它们
            if '"' in value and not (value.startswith('{') or value.startswith('[')):
                # 对于纯文本值，将嵌套引号转义
                value_escaped = value.replace('"', '\\"')
                return f'"{key}": "{value_escaped}"'
            return f'"{key}": {value}'
        
        return re.sub(key_value_pattern, process_value, processed_text)

    def _find_outermost_json(self, text: str) -> Optional[str]:
        """寻找最外层的JSON对象，处理嵌套和不平衡的情况"""
        start_pos = text.find('{')
        if start_pos == -1:
            # 尝试数组格式
            start_pos = text.find('[')
            if start_pos == -1:
                return None
                
        # 追踪括号匹配
        opening_chars = {'{': '}', '[': ']'}
        closing_chars = {'}': '{', ']': '['}
        stack = []
        
        bracket_type = text[start_pos]  # '{' 或 '['
        
        for i in range(start_pos, len(text)):
            char = text[i]
            
            if char in opening_chars:
                stack.append(char)
            elif char in closing_chars:
                if not stack or closing_chars[char] != stack[-1]:
                    # 不匹配的闭合括号，尝试跳过
                    continue
                stack.pop()
                
                # 如果找到匹配的最外层括号
                if not stack:
                    return text[start_pos:i+1]
                    
        # 如果没有找到完整匹配，但至少有开始括号
        # 尝试修复到合理位置结束
        if stack and len(stack) == 1 and stack[0] == bracket_type:
            # 寻找合理的结束位置
            for i in range(len(text)-1, start_pos, -1):
                # 找到文本中最后一个可能的结束括号
                if text[i] == opening_chars[bracket_type]:
                    return text[start_pos:i+1]
                    
        return None

    def _reconstruct_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试从文本中提取关键部分并重建JSON结构"""
        result = {}
        
        # 尝试提取学生分数部分
        student_scores_pattern = r'[\'"]?student_scores[\'"]?\s*[=:]\s*(\{[\s\S]*?\})'
        student_match = re.search(student_scores_pattern, text)
        
        if student_match:
            scores_text = student_match.group(1)
            try:
                # 尝试多种方法解析分数
                for method in [self._fix_common_json_issues, self._aggressive_json_fix, self._handle_nested_quotes]:
                    try:
                        cleaned_scores = method(scores_text)
                        result["student_scores"] = json.loads(cleaned_scores)
                        break
                    except json.JSONDecodeError:
                        continue
                
                if "student_scores" not in result:
                    # 手动提取键值对
                    scores_content = student_match.group(1)
                    score_pattern = r'[\'"]?([^\'",]+)[\'"]?\s*:\s*([\'"].*?[\'"]|\{.*?\}|\d+(?:\.\d+)?)'
                    score_pairs = re.findall(score_pattern, scores_content)
                    
                    manual_scores = {}
                    for k, v in score_pairs:
                        key = k.strip().replace('"', '').replace("'", '')
                        # 处理不同类型的值
                        if v.replace('.', '', 1).isdigit():
                            manual_scores[key] = float(v)
                        elif v.startswith('{'):
                            try:
                                # 尝试解析嵌套对象
                                obj_value = json.loads(self._fix_common_json_issues(v))
                                manual_scores[key] = obj_value
                            except:
                                manual_scores[key] = v
                        else:
                            # 去除引号
                            manual_scores[key] = v.strip('"\'')
                            
                    result["student_scores"] = manual_scores
            except Exception as e:
                logging.error(f"重建学生分数失败: {str(e)}")
                
        # 尝试提取评分标准
        grading_pattern = r'[\'"]?grading_standard[\'"]?\s*[=:]\s*["\']?([^"\'\}\]]+)["\']?'
        grading_match = re.search(grading_pattern, text)
        
        if grading_match:
            result["grading_standard"] = grading_match.group(1).strip()
            
        # 只有在至少找到一个关键部分时才返回结果
        return result if result else None

    def _extract_scoring_data(self, text: str) -> Optional[Dict[str, Any]]:
        """专门针对评分数据格式设计的提取方法"""
        # 尝试识别包含学生姓名、分数和评分标准的模式
        student_pattern = r'[\{\s]*[\'"]?([\u4e00-\u9fa5a-zA-Z0-9]+)[\'"]?\s*:\s*\{([^}]+)\}'
        student_matches = re.findall(student_pattern, text)
        
        if not student_matches:
            return None
            
        result = {}
        for student_name, details in student_matches:
            # 提取分数
            score_match = re.search(r'[\'"]?score[\'"]?\s*:\s*(\d+(?:\.\d+)?)', details)
            score = float(score_match.group(1)) if score_match else None
            
            # 提取评分标准 - 这部分可能包含复杂文本和嵌套引号
            criteria_match = re.search(r'[\'"]?scoring_criteria[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]', details)
            criteria = criteria_match.group(1) if criteria_match else ""
            
            if not criteria and score:
                # 尝试提取剩余所有内容作为评分标准
                criteria_alt_match = re.search(r'[\'"]?scoring_criteria[\'"]?\s*:\s*(.+)', details)
                if criteria_alt_match:
                    criteria_text = criteria_alt_match.group(1).strip()
                    # 去除开头和结尾的引号
                    criteria = criteria_text.strip('\'"')
            
            # 构建学生数据
            student_data = {}
            if score is not None:
                student_data['score'] = score
            if criteria:
                student_data['scoring_criteria'] = criteria
                
            if student_data:  # 只有在有数据时才添加
                result[student_name] = student_data
                
        return {"student_scores": result} if result else None
