from nicegui import ui, app
from utils.config import Config
from utils.my_log import logger
import json
import subprocess


def init():
    """
    初始化基本配置
    """
    global config_path, config
    config_path = 'config/config.json'
    # 实例化配置类
    config = Config(config_path)


# 初始化基本配置
init()

# 暗夜模式
dark = ui.dark_mode()


"""
                                                                                                    
                                               .@@@@@                           @@@@@.              
                                               .@@@@@                           @@@@@.              
        ]]]]]   .]]]]`   .]]]]`   ,]@@@@@\`    .@@@@@,/@@@\`   .]]]]]   ]]]]]`  ]]]]].              
        =@@@@^  =@@@@@`  =@@@@. =@@@@@@@@@@@\  .@@@@@@@@@@@@@  *@@@@@   @@@@@^  @@@@@.              
         =@@@@ ,@@@@@@@ .@@@@` =@@@@^   =@@@@^ .@@@@@`  =@@@@^ *@@@@@   @@@@@^  @@@@@.              
          @@@@^@@@@\@@@^=@@@^  @@@@@@@@@@@@@@@ .@@@@@   =@@@@@ *@@@@@   @@@@@^  @@@@@.              
          ,@@@@@@@^ \@@@@@@@   =@@@@^          .@@@@@.  =@@@@^ *@@@@@  .@@@@@^  @@@@@.              
           =@@@@@@  .@@@@@@.    \@@@@@]/@@@@@` .@@@@@@]/@@@@@. .@@@@@@@@@@@@@^  @@@@@.              
            \@@@@`   =@@@@^      ,\@@@@@@@@[   .@@@@^\@@@@@[    .\@@@@@[=@@@@^  @@@@@.    
            
"""
# 配置
webui_ip = config.get("webui", "ip")
webui_port = config.get("webui", "port")
webui_title = config.get("webui", "title")


# def create_config_ui(config_data, parent_key=''):
#     """递归创建配置UI"""
#     for key, value in config_data.items():
#         current_key = f"{parent_key}.{key}" if parent_key else key

#         if isinstance(value, dict):
#             with ui.expansion(key):
#                 create_config_ui(value, current_key)
#         else:
#             if isinstance(value, bool):
#                 ui.switch(f"{key}", value=value).bind_value(
#                     lambda v, k=current_key: update_config(k, v))
#             elif isinstance(value, (int, float)):
#                 ui.number(f"{key}", value=value).bind_value(
#                     lambda v, k=current_key: update_config(k, v))
#             elif isinstance(value, list):
#                 ui.textarea(f"{key}", value=str(value)).bind_value(
#                     lambda v, k=current_key: update_config(k, eval(v)))
#             elif value is None:
#                 ui.input(f"{key}", value='').bind_value(
#                     lambda v, k=current_key: update_config(k, v if v else None))
#             else:
#                 ui.input(f"{key}", value=str(value)).bind_value(
#                     lambda v, k=current_key: update_config(k, v))


def update_config(key_path, value):
    """更新配置"""
    keys = key_path.split('.')
    current = config.config
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value
    save_config(config.config)


def save_config(new_config):
    """保存配置到文件"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=4, ensure_ascii=False)
    logger.info('配置已保存')


# 页面滑到顶部
def scroll_to_top():
    # 这段JavaScript代码将页面滚动到顶部
    ui.run_javascript("window.scrollTo(0, 0);")   


# 创建配置界面
with ui.card().classes('w-full'):
    ui.label('配置管理').classes('text-h6 q-mb-md')
    create_config_ui(config.config)

ui.run(host=webui_ip, port=webui_port, title=webui_title,
       language="zh-CN", dark=False, reload=False)
