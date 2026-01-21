import json
import glob
import logging
import xlrd
from xlutils.copy import copy
import os
import sys
from typing import Dict, Optional, Tuple
import argparse


class ScoreProcessor:
    """可复用的成绩处理器"""

    def __init__(self, config_path: str = None):
        """初始化成绩处理器

        Args:
            config_path: 配置文件路径，如果不提供则使用默认配置
        """
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "pulling_students_up": True,
            "normalized_min": 60,
            "normalized_max": 85,
            "original_min": 20,
            "original_max": 85
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置和用户配置
                default_config.update(config)
            except Exception as e:
                print(f"警告：无法加载配置文件 {config_path}，使用默认配置。错误：{e}")

        return default_config

    def normalize_score(self, student_scores: Dict[str, float]) -> Dict[str, float]:
        """对学生成绩进行归一化处理

        根据homework_grader.py中的逻辑进行分数优化
        """
        def scale_score(score):
            # 对于原始分数特别高或者特别低的，直接返回原始分数，中间那些捞一手
            if score < self.config['original_min'] or score > self.config['original_max']:
                return score
            else:
                # 对其他分数进行缩放
                return score / 100 * (self.config['normalized_max'] - self.config['normalized_min']) + self.config['normalized_min']

        return {name: scale_score(score) for name, score in student_scores.items()}

    def extract_student_scores(self, json_file_path: str) -> Dict[str, float]:
        """从JSON文件中提取学生成绩

        Args:
            json_file_path: 原始成绩JSON文件路径

        Returns:
            学生姓名到成绩的映射字典
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            student_scores = {}
            for student_name, student_data in data.items():
                if isinstance(student_data, dict) and 'score' in student_data:
                    score = student_data['score']
                    if isinstance(score, (int, float)) and student_name.strip():
                        student_scores[student_name] = float(score)

            print(f"成功提取 {len(student_scores)} 名学生的成绩")
            return student_scores

        except Exception as e:
            print(f"读取JSON文件失败: {e}")
            return {}

    def create_normalized_score_file(self, student_scores: Dict[str, float], output_path: str):
        """创建标准化的成绩JSON文件

        Args:
            student_scores: 学生成绩字典
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(student_scores, f, ensure_ascii=False, indent=2)
            print(f"标准化成绩文件已保存到: {output_path}")
        except Exception as e:
            print(f"保存标准化成绩文件失败: {e}")

    def update_excel_file(self, excel_file_path: str, student_scores: Dict[str, float],
                          output_path: str = None) -> bool:
        """更新Excel文件中的学生成绩

        使用与file_manager.py相同的方法处理Excel文件

        Args:
            excel_file_path: Excel文件路径
            student_scores: 学生成绩字典
            output_path: 输出文件路径，如果为None则覆盖原文件

        Returns:
            是否更新成功
        """
        try:
            # 使用xlrd读取Excel文件
            workbook = xlrd.open_workbook(
                excel_file_path, formatting_info=True)
            sheet = workbook.sheet_by_index(0)

            print(f"Excel文件读取成功，共 {sheet.nrows} 行数据")

            # 查找学生姓名列和分数列
            student_name_col_idx = None
            score_col_idx = None

            # 检查第1行（索引1）的表头
            for col in range(sheet.ncols):
                header = sheet.cell_value(1, col)
                if "学生姓名" in str(header):
                    student_name_col_idx = col
                elif "分数" in str(header):
                    score_col_idx = col

            if student_name_col_idx is None or score_col_idx is None:
                print("错误：未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")
                return False

            print(f"识别到学生姓名列: 第{student_name_col_idx + 1}列")
            print(f"识别到分数列: 第{score_col_idx + 1}列")

            # 使用xlutils.copy创建可写的工作簿副本
            new_workbook = copy(workbook)
            new_sheet = new_workbook.get_sheet(0)

            # 更新成绩（从第2行开始，索引为2）
            updated_count = 0
            for row in range(2, sheet.nrows):
                student_name = str(sheet.cell_value(
                    row, student_name_col_idx)).strip()
                if student_name in student_scores:
                    new_sheet.write(row, score_col_idx,
                                    student_scores[student_name])
                    updated_count += 1

            # 保存文件
            output_file = output_path if output_path else excel_file_path
            new_workbook.save(output_file)

            print(f"成功更新 {updated_count} 名学生的成绩")
            print(f"Excel文件已保存到: {output_file}")
            return True

        except Exception as e:
            print(f"更新Excel文件失败: {e}")
            return False

    def process_homework_scores(self, original_json_path: str, excel_template_path: str,
                                output_excel_path: str = None,
                                normalized_json_path: str = None) -> bool:
        """处理作业成绩的主函数

        Args:
            original_json_path: 原始成绩JSON文件路径
            excel_template_path: Excel模版文件路径
            output_excel_path: 输出Excel文件路径，如果为None则覆盖原文件
            normalized_json_path: 标准化成绩JSON输出路径

        Returns:
            是否处理成功
        """
        print("开始处理作业成绩...")
        print(f"配置信息: 分数优化={self.config['pulling_students_up']}")

        # 1. 提取学生成绩
        student_scores = self.extract_student_scores(original_json_path)
        if not student_scores:
            print("错误：未能提取到有效的学生成绩")
            return False

        # 2. 根据配置决定是否进行分数优化
        final_scores = student_scores.copy()
        if self.config['pulling_students_up']:
            print("正在进行分数优化...")
            final_scores = self.normalize_score(student_scores)
            print(
                f"分数优化完成，优化范围: {self.config['original_min']}-{self.config['original_max']} -> {self.config['normalized_min']}-{self.config['normalized_max']}")
        else:
            print("跳过分数优化，使用原始分数")

        # 3. 保存标准化成绩文件（如果指定了路径）
        if normalized_json_path:
            self.create_normalized_score_file(
                final_scores, normalized_json_path)

        # 4. 更新Excel文件
        success = self.update_excel_file(
            excel_template_path, final_scores, output_excel_path)

        if success:
            print("作业成绩处理完成！")
        else:
            print("作业成绩处理失败！")

        return success


def main():
    """命令行入口函数"""
    json_file = '/Users/jixiaojian/Desktop/code/Chaoxing_Homework/homework/计算机应用（3+2）2401/管理用户组作答时间：03-13 15_47至  03-13 23_47/original_student_score.json'

    normalized_json_file = '/Users/jixiaojian/Desktop/code/Chaoxing_Homework/homework/计算机应用（3+2）2401/管理用户组作答时间：03-13 15_47至  03-13 23_47/normalized_student_score.json'

    excel_file = '/Users/jixiaojian/Desktop/code/Chaoxing_Homework/homework/计算机应用（3+2）2401/管理用户组作答时间：03-13 15_47至  03-13 23_47/管理用户组.xls'

    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='处理作业成绩')
    parser.add_argument('--original_json',
                        default=json_file, help='原始成绩JSON文件路径')
    parser.add_argument('--excel_template',
                        default=excel_file, help='Excel模版文件路径')
    parser.add_argument('--output_excel', help='输出Excel文件路径（可选，默认覆盖原文件）')
    parser.add_argument('--normalized_json', help='标准化成绩JSON输出路径（可选）')
    parser.add_argument('--config', help='配置文件路径（可选）')

    args = parser.parse_args()

    # 创建处理器
    processor = ScoreProcessor(args.config)

    # 处理成绩
    success = processor.process_homework_scores(
        original_json_path=args.original_json,
        excel_template_path=args.excel_template,
        output_excel_path=args.output_excel,
        normalized_json_path=args.normalized_json
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
