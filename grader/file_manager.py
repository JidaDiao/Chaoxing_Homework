import os
import json
import glob
import logging
import xlrd
from xlutils.copy import copy
from typing import Dict, List, Any
from .interface import IFileManager


class FileManager(IFileManager):
    """文件管理器类，负责文件操作，包括读写JSON、Excel等
    
    该类实现了IFileManager接口，提供了保存成绩到Excel文件、
    导入JSON文件和保存JSON文件的功能。
    
    Attributes:
        None
    """
    
    @staticmethod
    def save_grades(scores_to_save: Dict[str, float]) -> Dict[str, float]:
        """将成绩保存到Excel文件
        
        将归一化后的成绩保存到当前工作路径下唯一的Excel文件中（学习通导入模版）。
        
        Args:
            scores_to_save: 需要保存的成绩字典
            
        Returns:
            保存的成绩字典
            
        Raises:
            ValueError: 当Excel文件中未找到必要的列时抛出
        """
        xls_file = glob.glob("*.xls")[0]
        workbook = xlrd.open_workbook(xls_file, formatting_info=True)
        sheet = workbook.sheet_by_index(0)

        student_name_col_idx = None
        score_col_idx = None

        for col in range(sheet.ncols):
            header = sheet.cell_value(1, col)
            if "学生姓名" in header:
                student_name_col_idx = col
            elif "分数" in header:
                score_col_idx = col

        if student_name_col_idx is None or score_col_idx is None:
            logging.error("未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")
            raise ValueError("未找到'学生姓名'或'分数'列，请检查表头是否包含这些字段！")

        new_workbook = copy(workbook)
        new_sheet = new_workbook.get_sheet(0)

        for row in range(2, sheet.nrows):
            student_name = sheet.cell_value(row, student_name_col_idx)
            if student_name in scores_to_save:
                new_sheet.write(row, score_col_idx,
                               scores_to_save[student_name])

        new_workbook.save(xls_file)
        logging.info("分数更新完成！")
        return scores_to_save
    
    @staticmethod
    def import_json_file(file_path: str) -> Dict[str, Any]:
        """导入JSON文件
        
        从指定路径导入JSON文件并返回解析后的数据。
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            导入的JSON数据
            
        Raises:
            FileNotFoundError: 当文件不存在时抛出
            json.JSONDecodeError: 当JSON解析失败时抛出
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            logging.error(f"JSON解析错误: {str(e)}")
            raise
    
    @staticmethod
    def save_json_file(data: Dict[str, Any], file_path: str, indent: int = 4, 
                      sort_keys: bool = True, ensure_ascii: bool = False) -> None:
        """保存JSON文件
        
        将数据保存为JSON文件。
        
        Args:
            data: 需要保存的数据
            file_path: 保存路径
            indent: 缩进空格数
            sort_keys: 是否对键进行排序
            ensure_ascii: 是否确保ASCII编码
            
        Raises:
            IOError: 当文件写入失败时抛出
        """
        try:
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(
                    data,
                    json_file,
                    indent=indent,
                    sort_keys=sort_keys,
                    ensure_ascii=ensure_ascii
                )
            logging.info(f"JSON文件已保存: {file_path}")
        except IOError as e:
            logging.error(f"保存JSON文件时出错: {str(e)}")
            raise
    
    @staticmethod
    def read_grading_standard(file_path: str = "./评分标准.md") -> str:
        """读取评分标准文件
        
        从指定路径读取评分标准文件内容。
        
        Args:
            file_path: 评分标准文件路径，默认为"./评分标准.md"
            
        Returns:
            评分标准文件内容
            
        Raises:
            FileNotFoundError: 当文件不存在时抛出
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"评分标准文件不存在: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            grading_standard = f.read()
        return grading_standard
    
    @staticmethod
    def save_grading_standard(grading_standard: str, file_path: str = "评分标准.md") -> None:
        """保存评分标准到文件
        
        将评分标准内容保存到指定路径。
        
        Args:
            grading_standard: 评分标准内容
            file_path: 保存路径，默认为"评分标准.md"
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(grading_standard)
        logging.info(f"评分标准已保存: {file_path}") 