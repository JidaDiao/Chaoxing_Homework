import json

def import_json_file(file_path):
    """
    导入JSON文件并返回其内容。
    
    :param file_path: JSON文件的路径
    :return: 解析后的JSON内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"JSON文件解析错误: {file_path}")
        return None
