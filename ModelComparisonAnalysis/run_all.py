#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import webbrowser
import time
import sys

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 更改工作目录到脚本所在目录
os.chdir(current_dir)

def print_header(message):
    """打印带格式的标题"""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)

def check_requirements():
    """检查所需的依赖包是否已安装"""
    required_packages = [
        'numpy', 'pandas', 'matplotlib', 'seaborn', 
        'scipy', 'scikit-learn'
    ]
    
    print_header("检查必要依赖...")
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} 未安装")
    
    if missing_packages:
        print("\n需要安装以下依赖包：")
        packages_str = " ".join(missing_packages)
        cmd = f"pip install {packages_str}"
        print(f"\n建议执行: {cmd}")
        
        choice = input("\n是否自动安装依赖包？(y/n): ")
        if choice.lower() == 'y':
            print("\n安装依赖包中...")
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("依赖包安装完成！")
        else:
            print("\n请手动安装依赖包后再运行此脚本")
            sys.exit(1)

def run_analysis():
    """运行分析脚本"""
    print_header("开始运行分析脚本...")
    start_time = time.time()
    
    try:
        subprocess.run([sys.executable, 'run_analysis.py'], check=True)
        print(f"\n分析耗时: {time.time() - start_time:.2f} 秒")
    except subprocess.CalledProcessError as e:
        print(f"运行分析脚本时发生错误: {e}")
        sys.exit(1)

def open_results():
    """打开分析结果"""
    # 确保输出目录存在
    if not os.path.exists('analysis_results'):
        print("错误: 未找到分析结果目录!")
        return
    
    # 检查是否有分析报告
    report_path = 'analysis_report.md'
    if not os.path.exists(report_path):
        print("错误: 未找到分析报告!")
        return
    
    print_header("分析完成!")
    print("\n分析报告已生成: analysis_report.md")
    print("可视化图表已保存到: analysis_results/ 目录")
    
    # 列出生成的图表
    print("\n生成的可视化图表:")
    for i, filename in enumerate(sorted(os.listdir('analysis_results')), 1):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            print(f"{i:2d}. {filename}")
    
    # 询问是否打开报告
    choice = input("\n是否打开分析报告? (y/n): ")
    if choice.lower() == 'y':
        report_url = f"file://{os.path.abspath(report_path)}"
        try:
            webbrowser.open(report_url)
        except Exception as e:
            print(f"打开报告时出错: {e}")
            print(f"请手动打开报告文件: {report_path}")

def main():
    """主函数"""
    print_header("不同模型自动评分系统对比分析")
    print("\n此程序将分析不同模型对学生作业的评分结果，生成对比分析报告和可视化图表。")
    
    # 检查依赖
    check_requirements()
    
    # 运行分析
    run_analysis()
    
    # 展示结果
    open_results()
    
    print("\n程序执行完毕!")

if __name__ == "__main__":
    main() 