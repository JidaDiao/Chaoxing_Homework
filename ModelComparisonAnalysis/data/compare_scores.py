import json
import os
import pandas as pd
import matplotlib.pyplot as plt

# 定义数据目录和文件夹名称
data_dir = os.path.dirname(os.path.abspath(__file__))
folders = ['grok+grok', 'grok+qwenvl', 'qwenvl+qwenvl']

# 创建一个字典来存储所有学生的分数
all_scores = {}

# 遍历每个文件夹，读取JSON文件并提取分数
for folder in folders:
    json_path = os.path.join(data_dir, folder, 'original_student_score.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 提取每个学生的分数
        for student, info in data.items():
            if student not in all_scores:
                all_scores[student] = {}
            
            # 存储该文件夹下的分数
            all_scores[student][folder] = info['score']
    except Exception as e:
        print(f"读取文件 {json_path} 时出错: {e}")

# 创建DataFrame进行比较
df = pd.DataFrame.from_dict(all_scores, orient='index')

# 重命名列以便更好地理解
df.columns = ['Grok-Grok评分', 'Grok-QwenVL评分', 'QwenVL-QwenVL评分']

# 计算平均分
df['平均分'] = df.mean(axis=1)

# 计算标准差（评分一致性）
df['标准差'] = df.iloc[:, 0:3].std(axis=1)

# 按平均分排序
df_sorted = df.sort_values('平均分', ascending=False)

# 保存为CSV文件
csv_path = os.path.join(data_dir, 'student_scores_comparison.csv')
df_sorted.to_csv(csv_path, encoding='utf-8-sig')  # 使用utf-8-sig以支持Excel正确显示中文

# 保存为Excel文件
excel_path = os.path.join(data_dir, 'student_scores_comparison.xlsx')
df_sorted.to_excel(excel_path)

print(f"比较结果已保存到: {csv_path} 和 {excel_path}")

# 创建可视化图表
plt.figure(figsize=(15, 10))

# 绘制每个模型组合的分数分布
plt.subplot(2, 2, 1)
df.boxplot(column=['Grok-Grok评分', 'Grok-QwenVL评分', 'QwenVL-QwenVL评分'])
plt.title('不同模型组合的分数分布')
plt.ylabel('分数')

# 绘制前10名学生的分数比较
plt.subplot(2, 2, 2)
top10 = df_sorted.head(10)
top10[['Grok-Grok评分', 'Grok-QwenVL评分', 'QwenVL-QwenVL评分']].plot(kind='bar', ax=plt.gca())
plt.title('前10名学生的分数比较')
plt.ylabel('分数')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# 绘制标准差分布（评分一致性）
plt.subplot(2, 2, 3)
plt.hist(df['标准差'], bins=10)
plt.title('评分标准差分布')
plt.xlabel('标准差')
plt.ylabel('学生数量')

# 绘制散点图：比较不同模型组合的评分相关性
plt.subplot(2, 2, 4)
plt.scatter(df['Grok-Grok评分'], df['QwenVL-QwenVL评分'], alpha=0.6)
plt.title('Grok-Grok vs QwenVL-QwenVL评分相关性')
plt.xlabel('Grok-Grok评分')
plt.ylabel('QwenVL-QwenVL评分')
plt.grid(True, linestyle='--', alpha=0.7)

# 保存图表
plt.tight_layout()
plot_path = os.path.join(data_dir, 'score_comparison_plots.png')
plt.savefig(plot_path, dpi=300)

print(f"可视化图表已保存到: {plot_path}")

# 打印一些统计信息
print("\n各模型评分统计信息:")
print(df.describe())

# 计算模型间的相关性
print("\n模型评分相关性:")
print(df[['Grok-Grok评分', 'Grok-QwenVL评分', 'QwenVL-QwenVL评分']].corr())

# 找出评分差异最大的学生
df['最大差异'] = df.iloc[:, 0:3].max(axis=1) - df.iloc[:, 0:3].min(axis=1)
print("\n评分差异最大的5名学生:")
print(df.sort_values('最大差异', ascending=False).head(5)[['Grok-Grok评分', 'Grok-QwenVL评分', 'QwenVL-QwenVL评分', '最大差异']])