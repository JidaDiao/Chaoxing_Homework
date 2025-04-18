import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 确保输出目录存在
os.makedirs('analysis_results', exist_ok=True)

# 读取合并后的数据
try:
    merged_df = pd.read_csv('score_comparison.csv')
except FileNotFoundError:
    print("请先运行analyze_scores.py生成score_comparison.csv文件")
    exit(1)

# 计算每个学生在不同模型间的分数差异
merged_df['差异_grokgrok_grokqwen'] = merged_df['分数_grok_grok'] - merged_df['分数_grok_qwenvl']
merged_df['差异_grokgrok_qwenqwen'] = merged_df['分数_grok_grok'] - merged_df['分数_qwenvl_qwenvl']
merged_df['差异_grokqwen_qwenqwen'] = merged_df['分数_grok_qwenvl'] - merged_df['分数_qwenvl_qwenvl']
merged_df['最大差异'] = merged_df[['差异_grokgrok_grokqwen', '差异_grokgrok_qwenqwen', '差异_grokqwen_qwenqwen']].abs().max(axis=1)

# 保存增强的数据集
merged_df.to_csv('enhanced_comparison.csv', index=False, encoding='utf-8-sig')

# 1. 差异分布直方图
plt.figure(figsize=(15, 10))
bins = np.linspace(-30, 30, 20)

plt.hist(merged_df['差异_grokgrok_grokqwen'], bins=bins, alpha=0.5, label='Grok+Grok vs Grok+QwenVL')
plt.hist(merged_df['差异_grokgrok_qwenqwen'], bins=bins, alpha=0.5, label='Grok+Grok vs QwenVL+QwenVL')
plt.hist(merged_df['差异_grokqwen_qwenqwen'], bins=bins, alpha=0.5, label='Grok+QwenVL vs QwenVL+QwenVL')

plt.title('不同模型评分差异分布', fontsize=16)
plt.xlabel('分数差异', fontsize=14)
plt.ylabel('学生数量', fontsize=14)
plt.legend(fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.axvline(x=0, color='red', linestyle='--')
plt.savefig('analysis_results/score_difference_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 2. 学生分数差异热图
plt.figure(figsize=(15, 10))
difference_data = merged_df[['差异_grokgrok_grokqwen', '差异_grokgrok_qwenqwen', '差异_grokqwen_qwenqwen']].T
plt.imshow(difference_data, cmap='coolwarm', aspect='auto', vmin=-20, vmax=20)
plt.colorbar(label='分数差异')
plt.yticks([0, 1, 2], ['Grok+Grok vs\nGrok+QwenVL', 'Grok+Grok vs\nQwenVL+QwenVL', 'Grok+QwenVL vs\nQwenVL+QwenVL'])
plt.title('各学生在不同模型对之间的分数差异', fontsize=16)
plt.xlabel('学生编号', fontsize=14)
plt.tight_layout()
plt.savefig('analysis_results/student_difference_heatmap.png', dpi=300, bbox_inches='tight')
plt.close()

# 3. 最大差异排序
top_diff = merged_df.sort_values('最大差异', ascending=False).head(10)
plt.figure(figsize=(12, 8))
bars = plt.bar(top_diff['学生'], top_diff['最大差异'], color='skyblue')
plt.title('分数差异最大的10位学生', fontsize=16)
plt.xlabel('学生', fontsize=14)
plt.ylabel('最大绝对差异', fontsize=14)
plt.xticks(rotation=45, ha='right')
plt.grid(True, linestyle='--', alpha=0.5, axis='y')

# 在柱状图上标注具体数值
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
            f'{height:.1f}',
            ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig('analysis_results/top_difference_students.png', dpi=300, bbox_inches='tight')
plt.close()

# 4. 分数差异关系散点图
plt.figure(figsize=(15, 8))
scatter = plt.scatter(
    merged_df['分数_grok_grok'], 
    merged_df['差异_grokgrok_qwenqwen'],
    c=merged_df['分数_qwenvl_qwenvl'], 
    cmap='viridis', 
    alpha=0.7,
    s=100
)
plt.colorbar(scatter, label='QwenVL+QwenVL分数')
plt.axhline(y=0, color='red', linestyle='--')
plt.title('Grok+Grok分数与其与QwenVL+QwenVL的差异关系', fontsize=16)
plt.xlabel('Grok+Grok分数', fontsize=14)
plt.ylabel('Grok+Grok与QwenVL+QwenVL的差异', fontsize=14)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('analysis_results/score_difference_relationship.png', dpi=300, bbox_inches='tight')
plt.close()

# 5. 分数段差异分析
def score_category(score):
    if score >= 90:
        return '优秀(90-100)'
    elif score >= 80:
        return '良好(80-89)'
    elif score >= 70:
        return '中等(70-79)'
    elif score >= 60:
        return '及格(60-69)'
    else:
        return '不及格(<60)'

# 为每个模型的分数添加类别
for col in ['分数_grok_grok', '分数_grok_qwenvl', '分数_qwenvl_qwenvl']:
    merged_df[f'{col}_类别'] = merged_df[col].apply(score_category)

# 计算每对模型的混淆矩阵
pairs = [
    ('Grok+Grok', 'Grok+QwenVL', '分数_grok_grok_类别', '分数_grok_qwenvl_类别'),
    ('Grok+Grok', 'QwenVL+QwenVL', '分数_grok_grok_类别', '分数_qwenvl_qwenvl_类别'),
    ('Grok+QwenVL', 'QwenVL+QwenVL', '分数_grok_qwenvl_类别', '分数_qwenvl_qwenvl_类别')
]

categories = ['优秀(90-100)', '良好(80-89)', '中等(70-79)', '及格(60-69)', '不及格(<60)']

for model1, model2, cat1, cat2 in pairs:
    # 计算混淆矩阵
    matrix = pd.crosstab(merged_df[cat1], merged_df[cat2], 
                         rownames=[f'{model1}'], colnames=[f'{model2}'])
    
    # 重新排序索引和列
    matrix = matrix.reindex(categories, axis=0)
    matrix = matrix.reindex(categories, axis=1)
    matrix = matrix.fillna(0)
    
    # 创建热图
    plt.figure(figsize=(10, 8))
    sns.heatmap(matrix, annot=True, fmt='g', cmap='Blues')
    plt.title(f'{model1} vs {model2} 评分等级一致性', fontsize=16)
    plt.tight_layout()
    plt.savefig(f'analysis_results/{model1.replace("+", "_")}_{model2.replace("+", "_")}_confusion.png', 
                dpi=300, bbox_inches='tight')
    plt.close()

# 6. 聚类分析 - 根据三个模型的分数进行学生聚类
# 准备聚类数据
cluster_data = merged_df[['分数_grok_grok', '分数_grok_qwenvl', '分数_qwenvl_qwenvl']].copy()
# 标准化数据
scaler = StandardScaler()
scaled_data = scaler.fit_transform(cluster_data)

# 确定最佳聚类数
inertia = []
for k in range(1, 10):
    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(scaled_data)
    inertia.append(kmeans.inertia_)

# 绘制肘部图
plt.figure(figsize=(10, 6))
plt.plot(range(1, 10), inertia, marker='o')
plt.title('K均值聚类肘部图', fontsize=16)
plt.xlabel('聚类数量', fontsize=14)
plt.ylabel('惯性', fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.savefig('analysis_results/kmeans_elbow.png', dpi=300, bbox_inches='tight')
plt.close()

# 选择聚类数并进行聚类
n_clusters = 3  # 根据肘部图选择最佳聚类数
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
merged_df['聚类'] = kmeans.fit_predict(scaled_data)

# 可视化聚类结果
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')

colors = ['red', 'green', 'blue', 'purple', 'orange']
markers = ['o', '^', 's', 'D', 'p']

for i in range(n_clusters):
    cluster_data = merged_df[merged_df['聚类'] == i]
    ax.scatter(
        cluster_data['分数_grok_grok'],
        cluster_data['分数_grok_qwenvl'],
        cluster_data['分数_qwenvl_qwenvl'],
        c=colors[i % len(colors)],
        marker=markers[i % len(markers)],
        s=100,
        alpha=0.6,
        label=f'聚类 {i+1}'
    )

ax.set_xlabel('Grok+Grok分数')
ax.set_ylabel('Grok+QwenVL分数')
ax.set_zlabel('QwenVL+QwenVL分数')
ax.set_title('基于不同模型评分的学生聚类')
plt.legend()
plt.savefig('analysis_results/student_clusters_3d.png', dpi=300, bbox_inches='tight')
plt.close()

# 分析每个聚类的特征
cluster_stats = merged_df.groupby('聚类')[['分数_grok_grok', '分数_grok_qwenvl', '分数_qwenvl_qwenvl']].agg(['mean', 'std', 'min', 'max', 'count'])
cluster_stats.to_csv('analysis_results/cluster_statistics.csv', encoding='utf-8-sig')

print("分析完成！额外的结果已保存到analysis_results目录")
print("聚类统计数据:")
print(cluster_stats) 