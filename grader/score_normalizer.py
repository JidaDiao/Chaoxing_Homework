from typing import Dict
from grader.interfaces import ScoreNormalizer
import logging


class DefaultScoreNormalizer(ScoreNormalizer):
    """默认分数归一化处理实现
    
    对原始分数进行归一化处理，将分数映射到指定范围。
    """
    
    def normalize(self, scores: Dict, **kwargs) -> Dict:
        """归一化分数
        
        Args:
            scores: 原始分数
            **kwargs: 其他参数，如最小值、最大值等
            
        Returns:
            归一化后的分数
        """
        normalized_min = kwargs.get('normalized_min', 60)
        normalized_max = kwargs.get('normalized_max', 85)
        original_min = kwargs.get('original_min', 20)
        original_max = kwargs.get('original_max', 90)
        
        def scale_score(score):
            # 对于原始分数特别高或者特别低的，直接返回原始分数
            if score < original_min or score > original_max:
                return score
            else:
                # 对其他分数进行缩放
                return score / 100 * (normalized_max - normalized_min) + normalized_min
        
        return {name: scale_score(score) for name, score in scores.items()}