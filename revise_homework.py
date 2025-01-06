from utils import *

homework_data = import_json_file('/Users/jixiaojian/Library/Application Support/Mountain Duck/Volumes.noindex/www.jidadiao.fun – WebDAV (HTTPS).localized/SATA硬盘2/工作/东方的工作/任务：DHCP服务器搭建.json')
task_name_list = list(homework_data.keys())
len_task = len(task_name_list)

for i in range(len_task):
    task_description = homework_data[task_name_list[i]]['description']
    task_correct_answer = homework_data[task_name_list[i]]['correct_answer']
    print(task_description)
    print(task_correct_answer)
