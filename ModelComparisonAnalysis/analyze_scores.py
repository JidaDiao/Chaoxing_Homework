import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_squared_error
import matplotlib.font_manager as fm
import os

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
def load_scores(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# 加载数据
grok_grok_scores = load_scores('data/grok+grok/normalized_student_score.json')
grok_qwenvl_scores = load_scores('data/grok+qwenvl/normalized_student_score.json')
qwenvl_qwenvl_scores = load_scores('data/qwenvl+qwenvl/normalized_student_score.json')

# 转换为DataFrame
def convert_to_df(scores_dict):
    return pd.DataFrame(list(scores_dict.items()), columns=['学生', '分数'])

# 创建数据帧
grok_grok_df = convert_to_df(grok_grok_scores)
grok_qwenvl_df = convert_to_df(grok_qwenvl_scores)
qwenvl_qwenvl_df = convert_to_df(qwenvl_qwenvl_scores)

# 合并数据帧
merged_df = pd.merge(grok_grok_df, grok_qwenvl_df, on='学生', how='outer', suffixes=('_grok_grok', '_grok_qwenvl'))
merged_df = pd.merge(merged_df, qwenvl_qwenvl_df, on='学生', how='outer', suffixes=('', '_qwenvl_qwenvl'))
merged_df.rename(columns={'分数': '分数_qwenvl_qwenvl'}, inplace=True)

# 处理缺失值
merged_df.fillna(0, inplace=True)

# 保存合并的数据
merged_df.to_csv('score_comparison.csv', index=False, encoding='utf-8-sig')

# 创建输出目录
os.makedirs('analysis_results', exist_ok=True)

# 1. 分数分布直方图对比
plt.figure(figsize=(15, 10))
bins = np.linspace(0, 100, 15)

plt.hist(merged_df['分数_grok_grok'], bins=bins, alpha=0.5, label='Grok+Grok')
plt.hist(merged_df['分数_grok_qwenvl'], bins=bins, alpha=0.5, label='Grok+QwenVL')
plt.hist(merged_df['分数_qwenvl_qwenvl'], bins=bins, alpha=0.5, label='QwenVL+QwenVL')

plt.title('不同模型评分分布对比', fontsize=16)
plt.xlabel('分数', fontsize=14)
plt.ylabel('学生数量', fontsize=14)
plt.legend(fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.savefig('analysis_results/score_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 2. 箱型图比较
plt.figure(figsize=(12, 8))
box_data = [
    merged_df['分数_grok_grok'].values,
    merged_df['分数_grok_qwenvl'].values,
    merged_df['分数_qwenvl_qwenvl'].values
]

plt.boxplot(box_data, labels=['Grok+Grok', 'Grok+QwenVL', 'QwenVL+QwenVL'])
plt.title('不同模型评分箱型图对比', fontsize=16)
plt.ylabel('分数', fontsize=14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.savefig('analysis_results/score_boxplot.png', dpi=300, bbox_inches='tight')
plt.close()

# 3. 相关性分析
correlation_matrix = merged_df[['分数_grok_grok', '分数_grok_qwenvl', '分数_qwenvl_qwenvl']].corr()

plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1, 
            xticklabels=['Grok+Grok', 'Grok+QwenVL', 'QwenVL+QwenVL'],
            yticklabels=['Grok+Grok', 'Grok+QwenVL', 'QwenVL+QwenVL'])
plt.title('模型评分相关性矩阵', fontsize=16)
plt.tight_layout()
plt.savefig('analysis_results/correlation_matrix.png', dpi=300, bbox_inches='tight')
plt.close()

# 4. 散点图矩阵
plt.figure(figsize=(15, 15))
sns.pairplot(merged_df[['分数_grok_grok', '分数_grok_qwenvl', '分数_qwenvl_qwenvl']], 
             diag_kind='kde',
             plot_kws={'alpha': 0.6, 's': 80, 'edgecolor': 'k'},
             diag_kws={'shade': True})
plt.savefig('analysis_results/pairplot.png', dpi=300, bbox_inches='tight')
plt.close()

# 5. 学生个体分数对比
plt.figure(figsize=(20, 10))
bar_width = 0.25
index = np.arange(len(merged_df))

plt.bar(index, merged_df['分数_grok_grok'], bar_width, label='Grok+Grok', alpha=0.7)
plt.bar(index + bar_width, merged_df['分数_grok_qwenvl'], bar_width, label='Grok+QwenVL', alpha=0.7)
plt.bar(index + 2*bar_width, merged_df['分数_qwenvl_qwenvl'], bar_width, label='QwenVL+QwenVL', alpha=0.7)

plt.xlabel('学生', fontsize=14)
plt.ylabel('分数', fontsize=14)
plt.title('各学生在不同模型下的得分对比', fontsize=16)
plt.xticks(index + bar_width, merged_df['学生'], rotation=90)
plt.legend()
plt.tight_layout()
plt.savefig('analysis_results/student_score_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

# 6. 计算统计指标
models = ['Grok+Grok', 'Grok+QwenVL', 'QwenVL+QwenVL']
columns = ['分数_grok_grok', '分数_grok_qwenvl', '分数_qwenvl_qwenvl']

# 计算基本统计量
stats = {
    '平均分': [merged_df[col].mean() for col in columns],
    '中位数': [merged_df[col].median() for col in columns],
    '标准差': [merged_df[col].std() for col in columns],
    '最高分': [merged_df[col].max() for col in columns],
    '最低分': [merged_df[col].min() for col in columns],
}

stats_df = pd.DataFrame(stats, index=models)
stats_df.to_csv('analysis_results/statistical_metrics.csv', encoding='utf-8-sig')

# 计算模型间的差异指标
print("模型间相关性和差异指标:")
pairs = [
    ('Grok+Grok vs Grok+QwenVL', '分数_grok_grok', '分数_grok_qwenvl'),
    ('Grok+Grok vs QwenVL+QwenVL', '分数_grok_grok', '分数_qwenvl_qwenvl'),
    ('Grok+QwenVL vs QwenVL+QwenVL', '分数_grok_qwenvl', '分数_qwenvl_qwenvl')
]

similarity_metrics = []

for pair_name, col1, col2 in pairs:
    pearson_corr, _ = pearsonr(merged_df[col1], merged_df[col2])
    spearman_corr, _ = spearmanr(merged_df[col1], merged_df[col2])
    mse = mean_squared_error(merged_df[col1], merged_df[col2])
    mean_abs_diff = np.mean(np.abs(merged_df[col1] - merged_df[col2]))
    
    similarity_metrics.append({
        '对比': pair_name,
        'Pearson相关系数': pearson_corr,
        'Spearman相关系数': spearman_corr,
        '均方误差(MSE)': mse,
        '平均绝对差异': mean_abs_diff
    })

similarity_df = pd.DataFrame(similarity_metrics)
similarity_df.to_csv('analysis_results/similarity_metrics.csv', index=False, encoding='utf-8-sig')

# 打印分析结果摘要
print("分析完成！结果已保存到analysis_results目录")
print("基本统计指标:")
print(stats_df)
print("\n相似度指标:")
print(similarity_df) 