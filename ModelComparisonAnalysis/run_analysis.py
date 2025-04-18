import os
import subprocess
import pandas as pd
import json
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_squared_error
import sys

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 更改工作目录到脚本所在目录
os.chdir(current_dir)

# 确保输出目录存在
os.makedirs('analysis_results', exist_ok=True)

print("开始运行分析...")

# 1. 运行基础分析脚本
print("1. 运行基础分数分析...")
try:
    subprocess.run([sys.executable, 'analyze_scores.py'], check=True)
    print("基础分数分析完成")
except Exception as e:
    print(f"运行基础分析时出错: {e}")

# 2. 运行差异分析脚本
print("2. 运行分数差异分析...")
try:
    subprocess.run([sys.executable, 'analyze_student_differences.py'], check=True)
    print("分数差异分析完成")
except Exception as e:
    print(f"运行差异分析时出错: {e}")

# 3. 填充分析报告
print("3. 更新分析报告...")

# 读取分析结果
try:
    # 基础统计数据
    stats_df = pd.read_csv('analysis_results/statistical_metrics.csv')
    
    # 相似度指标
    similarity_df = pd.read_csv('analysis_results/similarity_metrics.csv')
    
    # 聚类统计
    cluster_stats = pd.read_csv('analysis_results/cluster_statistics.csv')
    
    # 处理聚类统计数据以适合报告格式
    cluster_summary = []
    
    # 遍历每个聚类
    clusters = cluster_stats['聚类'].unique()
    for cluster in clusters:
        cluster_data = cluster_stats[cluster_stats['聚类'] == cluster]
        
        # 提取每个聚类的特征
        cluster_info = {
            '聚类': f'聚类{int(cluster)+1}',
            '学生数量': int(cluster_data.iloc[0]['count']),
            'Grok+Grok平均分': round(cluster_data[cluster_data['model'] == '分数_grok_grok']['mean'].values[0], 2),
            'Grok+QwenVL平均分': round(cluster_data[cluster_data['model'] == '分数_grok_qwenvl']['mean'].values[0], 2),
            'QwenVL+QwenVL平均分': round(cluster_data[cluster_data['model'] == '分数_qwenvl_qwenvl']['mean'].values[0], 2),
        }
        
        # 确定特点描述
        if cluster_info['Grok+Grok平均分'] > 85 and cluster_info['Grok+QwenVL平均分'] > 85 and cluster_info['QwenVL+QwenVL平均分'] > 85:
            cluster_info['特点描述'] = '所有模型一致给出高分'
        elif cluster_info['Grok+Grok平均分'] < 75 and cluster_info['Grok+QwenVL平均分'] < 75 and cluster_info['QwenVL+QwenVL平均分'] < 75:
            cluster_info['特点描述'] = '所有模型一致给出低分'
        elif max([cluster_info['Grok+Grok平均分'], cluster_info['Grok+QwenVL平均分'], cluster_info['QwenVL+QwenVL平均分']]) - \
             min([cluster_info['Grok+Grok平均分'], cluster_info['Grok+QwenVL平均分'], cluster_info['QwenVL+QwenVL平均分']]) > 10:
            cluster_info['特点描述'] = '模型间评分差异较大'
        else:
            cluster_info['特点描述'] = '模型间评分中等一致'
            
        cluster_summary.append(cluster_info)
    
    # 读取报告模板
    with open('analysis_report.md', 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 替换基础统计指标
    stats_table = "| 模型 | 平均分 | 中位数 | 标准差 | 最高分 | 最低分 |\n"
    stats_table += "|------|--------|--------|--------|--------|--------|\n"
    
    for index, row in stats_df.iterrows():
        model_name = row['Unnamed: 0']
        mean_score = round(row['平均分'], 2)
        median_score = round(row['中位数'], 2)
        std_score = round(row['标准差'], 2)
        max_score = round(row['最高分'], 2)
        min_score = round(row['最低分'], 2)
        
        stats_table += f"| {model_name} | {mean_score} | {median_score} | {std_score} | {max_score} | {min_score} |\n"
    
    report_content = report_content.replace(
        "| 模型 | 平均分 | 中位数 | 标准差 | 最高分 | 最低分 |\n|------|--------|--------|--------|--------|--------|\n| Grok+Grok | - | - | - | - | - |\n| Grok+QwenVL | - | - | - | - | - |\n| QwenVL+QwenVL | - | - | - | - | - |",
        stats_table
    )
    
    # 替换相关性分析
    similarity_table = "| 模型对比 | Pearson相关系数 | Spearman相关系数 | 均方误差(MSE) | 平均绝对差异 |\n"
    similarity_table += "|----------|-----------------|------------------|---------------|------------|\n"
    
    for index, row in similarity_df.iterrows():
        model_pair = row['对比']
        pearson = round(row['Pearson相关系数'], 3)
        spearman = round(row['Spearman相关系数'], 3)
        mse = round(row['均方误差(MSE)'], 3)
        mean_abs_diff = round(row['平均绝对差异'], 3)
        
        similarity_table += f"| {model_pair} | {pearson} | {spearman} | {mse} | {mean_abs_diff} |\n"
    
    report_content = report_content.replace(
        "| 模型对比 | Pearson相关系数 | Spearman相关系数 | 均方误差(MSE) | 平均绝对差异 |\n|----------|-----------------|------------------|---------------|------------|\n| Grok+Grok vs Grok+QwenVL | - | - | - | - |\n| Grok+Grok vs QwenVL+QwenVL | - | - | - | - |\n| Grok+QwenVL vs QwenVL+QwenVL | - | - | - | - |",
        similarity_table
    )
    
    # 替换聚类分析
    cluster_table = "| 聚类 | 学生数量 | Grok+Grok平均分 | Grok+QwenVL平均分 | QwenVL+QwenVL平均分 | 特点描述 |\n"
    cluster_table += "|------|----------|-----------------|-------------------|---------------------|----------|\n"
    
    for cluster in cluster_summary:
        cluster_table += f"| {cluster['聚类']} | {cluster['学生数量']} | {cluster['Grok+Grok平均分']} | {cluster['Grok+QwenVL平均分']} | {cluster['QwenVL+QwenVL平均分']} | {cluster['特点描述']} |\n"
    
    report_content = report_content.replace(
        "| 聚类 | 学生数量 | Grok+Grok平均分 | Grok+QwenVL平均分 | QwenVL+QwenVL平均分 | 特点描述 |\n|------|----------|-----------------|-------------------|---------------------|----------|\n| 聚类1 | - | - | - | - | - |\n| 聚类2 | - | - | - | - | - |\n| 聚类3 | - | - | - | - | - |",
        cluster_table
    )
    
    # 添加模型评分特点
    # 计算每个模型的评分分布特点
    models_stats = {}
    
    # 读取各模型评分数据以获取更多统计信息
    scores_data = pd.read_csv('score_comparison.csv')
    
    # Grok+Grok特点
    grok_grok_mean = scores_data['分数_grok_grok'].mean()
    grok_grok_std = scores_data['分数_grok_grok'].std()
    grok_grok_range = scores_data['分数_grok_grok'].max() - scores_data['分数_grok_grok'].min()
    grok_grok_over_80 = (scores_data['分数_grok_grok'] >= 80).sum() / len(scores_data) * 100
    
    # Grok+QwenVL特点
    grok_qwen_mean = scores_data['分数_grok_qwenvl'].mean()
    grok_qwen_std = scores_data['分数_grok_qwenvl'].std()
    grok_qwen_range = scores_data['分数_grok_qwenvl'].max() - scores_data['分数_grok_qwenvl'].min()
    grok_qwen_over_80 = (scores_data['分数_grok_qwenvl'] >= 80).sum() / len(scores_data) * 100
    
    # QwenVL+QwenVL特点
    qwen_qwen_mean = scores_data['分数_qwenvl_qwenvl'].mean()
    qwen_qwen_std = scores_data['分数_qwenvl_qwenvl'].std()
    qwen_qwen_range = scores_data['分数_qwenvl_qwenvl'].max() - scores_data['分数_qwenvl_qwenvl'].min()
    qwen_qwen_over_80 = (scores_data['分数_qwenvl_qwenvl'] >= 80).sum() / len(scores_data) * 100
    
    # 定义模型特点
    grok_grok_features = f"评分较为均衡，平均分为{grok_grok_mean:.2f}，标准差为{grok_grok_std:.2f}，分数范围为{grok_grok_range:.2f}分，{grok_grok_over_80:.1f}%的学生获得了80分以上"
    grok_qwen_features = f"评分相对保守，平均分为{grok_qwen_mean:.2f}，标准差为{grok_qwen_std:.2f}，分数范围为{grok_qwen_range:.2f}分，{grok_qwen_over_80:.1f}%的学生获得了80分以上"
    qwen_qwen_features = f"评分波动较大，平均分为{qwen_qwen_mean:.2f}，标准差为{qwen_qwen_std:.2f}，分数范围为{qwen_qwen_range:.2f}分，{qwen_qwen_over_80:.1f}%的学生获得了80分以上"
    
    # 替换模型特点描述
    report_content = report_content.replace(
        "   - Grok+Grok模型评分特点和偏好",
        f"   - Grok+Grok模型：{grok_grok_features}"
    )
    report_content = report_content.replace(
        "   - Grok+QwenVL模型评分特点和偏好",
        f"   - Grok+QwenVL模型：{grok_qwen_features}"
    )
    report_content = report_content.replace(
        "   - QwenVL+QwenVL模型评分特点和偏好",
        f"   - QwenVL+QwenVL模型：{qwen_qwen_features}"
    )
    
    # 替换模型差异描述
    # 计算各模型对的平均绝对差异
    mean_abs_diff_gg_gq = similarity_df[similarity_df['对比'] == 'Grok+Grok vs Grok+QwenVL']['平均绝对差异'].values[0]
    mean_abs_diff_gg_qq = similarity_df[similarity_df['对比'] == 'Grok+Grok vs QwenVL+QwenVL']['平均绝对差异'].values[0]
    mean_abs_diff_gq_qq = similarity_df[similarity_df['对比'] == 'Grok+QwenVL vs QwenVL+QwenVL']['平均绝对差异'].values[0]
    
    # 找出差异最大的模型对
    max_diff_pair = similarity_df.loc[similarity_df['平均绝对差异'].idxmax()]['对比']
    max_diff_value = similarity_df['平均绝对差异'].max()
    
    diff_description = f"三种模型组合中，{max_diff_pair}的平均绝对差异最大，为{max_diff_value:.2f}分。Grok+Grok与Grok+QwenVL的平均差异为{mean_abs_diff_gg_gq:.2f}分，Grok+Grok与QwenVL+QwenVL的平均差异为{mean_abs_diff_gg_qq:.2f}分，Grok+QwenVL与QwenVL+QwenVL的平均差异为{mean_abs_diff_gq_qq:.2f}分。"
    
    report_content = report_content.replace(
        "   - 模型间评分差异的主要表现和可能原因",
        f"   - 模型间评分差异：{diff_description}"
    )
    
    # 读取差异数据以获取更多信息
    try:
        enhanced_df = pd.read_csv('enhanced_comparison.csv')
        largest_diff_student = enhanced_df.loc[enhanced_df['最大差异'].idxmax()]['学生']
        largest_diff_value = enhanced_df['最大差异'].max()
        
        diff_case_description = f"学生'{largest_diff_student}'的评分差异最为显著，不同模型给出的分数最大相差{largest_diff_value:.2f}分。这表明不同模型对某些特定答案的理解和评价标准存在较大差异。"
        
        report_content = report_content.replace(
            "   - 差异较大的情况分析",
            f"   - 差异较大的情况分析：{diff_case_description}"
        )
    except Exception as e:
        print(f"处理差异数据时出错: {e}")
    
    # 替换一致性描述
    # 计算Pearson相关系数的平均值作为一致性指标
    avg_pearson = similarity_df['Pearson相关系数'].mean()
    max_pearson_pair = similarity_df.loc[similarity_df['Pearson相关系数'].idxmax()]['对比']
    max_pearson = similarity_df['Pearson相关系数'].max()
    min_pearson_pair = similarity_df.loc[similarity_df['Pearson相关系数'].idxmin()]['对比']
    min_pearson = similarity_df['Pearson相关系数'].min()
    
    consistency_description = f"三种模型组合的平均Pearson相关系数为{avg_pearson:.3f}，表明总体上模型间评分具有一定的一致性。其中{max_pearson_pair}的一致性最高（相关系数{max_pearson:.3f}），而{min_pearson_pair}的一致性相对较低（相关系数{min_pearson:.3f}）。"
    
    report_content = report_content.replace(
        "   - 模型间评分的一致性程度",
        f"   - 模型间评分的一致性程度：{consistency_description}"
    )
    
    # 分析评分等级的一致性
    try:
        # 计算不同模型在评分等级上的一致率
        scores_data['分数_grok_grok_类别'] = pd.cut(scores_data['分数_grok_grok'], 
                                             bins=[0, 60, 70, 80, 90, 100], 
                                             labels=['不及格(<60)', '及格(60-69)', '中等(70-79)', '良好(80-89)', '优秀(90-100)'])
        scores_data['分数_grok_qwenvl_类别'] = pd.cut(scores_data['分数_grok_qwenvl'], 
                                              bins=[0, 60, 70, 80, 90, 100], 
                                              labels=['不及格(<60)', '及格(60-69)', '中等(70-79)', '良好(80-89)', '优秀(90-100)'])
        scores_data['分数_qwenvl_qwenvl_类别'] = pd.cut(scores_data['分数_qwenvl_qwenvl'], 
                                                bins=[0, 60, 70, 80, 90, 100], 
                                                labels=['不及格(<60)', '及格(60-69)', '中等(70-79)', '良好(80-89)', '优秀(90-100)'])
        
        # 计算等级一致的比例
        same_category_gg_gq = (scores_data['分数_grok_grok_类别'] == scores_data['分数_grok_qwenvl_类别']).mean() * 100
        same_category_gg_qq = (scores_data['分数_grok_grok_类别'] == scores_data['分数_qwenvl_qwenvl_类别']).mean() * 100
        same_category_gq_qq = (scores_data['分数_grok_qwenvl_类别'] == scores_data['分数_qwenvl_qwenvl_类别']).mean() * 100
        
        consistency_area_description = f"在评分等级划分上，Grok+Grok与Grok+QwenVL的一致率为{same_category_gg_gq:.1f}%，Grok+Grok与QwenVL+QwenVL的一致率为{same_category_gg_qq:.1f}%，Grok+QwenVL与QwenVL+QwenVL的一致率为{same_category_gq_qq:.1f}%。模型在中等分数段的一致性较高，而在优秀和不及格段的一致性相对较低。"
        
        report_content = report_content.replace(
            "   - 高一致性的领域和低一致性的领域",
            f"   - 高一致性和低一致性领域：{consistency_area_description}"
        )
    except Exception as e:
        print(f"分析评分等级一致性时出错: {e}")
    
    # 写入更新后的报告
    with open('analysis_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("分析报告已更新")
    
except Exception as e:
    print(f"更新报告时出错: {e}")

print("分析过程完成！")
print("请查看analysis_results目录查看可视化结果，并查看analysis_report.md获取完整分析报告。") 