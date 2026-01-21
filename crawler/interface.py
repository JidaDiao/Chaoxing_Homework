from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# 登录策略模式接口


class LoginStrategy(ABC):
    """登录策略接口

    定义不同登录方式的统一接口，遵循策略设计模式。
    子类需要实现具体的登录逻辑。
    """

    @abstractmethod
    def login(self, driver: Any, login_url: str) -> bool:
        """执行登录操作

        Args:
            driver: 浏览器驱动实例
            login_url: 登录页面URL

        Returns:
            bool: 登录是否成功
        """
        pass

# WebDriver工厂模式接口


class WebDriverFactory(ABC):
    """WebDriver工厂接口

    定义创建WebDriver实例的接口，遵循工厂设计模式。
    子类需要实现具体的WebDriver创建逻辑。
    """

    @abstractmethod
    def create_driver(self) -> Any:
        """创建WebDriver实例

        Returns:
            Any: 浏览器驱动实例
        """
        pass

# 模板方法模式接口


class HomeworkProcessor(ABC):
    """作业处理接口

    定义作业处理的模板方法，遵循模板方法设计模式。
    子类需要实现具体的作业处理逻辑。
    """

    @abstractmethod
    def get_students_grading_url(self, homework_url: str) -> List[Dict[str, Any]]:
        """获取学生作业批阅链接列表

        Args:
            homework_url: 作业批阅页面URL

        Returns:
            List[Dict[str, Any]]: 学生作业批阅信息列表
        """
        pass

    @abstractmethod
    def process_student_data(self, student_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理学生作业数据

        Args:
            student_data: 学生作业数据列表

        Returns:
            Dict[str, Any]: 处理后的学生作业数据
        """
        pass

    @abstractmethod
    def process_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """处理最终结果数据

        Args:
            results: 学生作业处理结果

        Returns:
            Dict[str, Any]: 格式化后的最终结果
        """
        pass

    def process_homework(self, homework_grading_url: str) -> Optional[Dict[str, Any]]:
        """作业处理的模板方法

        定义了处理作业的标准流程：获取学生数据 -> 处理学生数据 -> 处理最终结果。

        Args:
            homework_grading_url: 作业批阅页面URL

        Returns:
            Optional[Dict[str, Any]]: 处理后的最终结果，失败则返回None
        """
        student_data = self.get_students_grading_url(homework_grading_url)
        if student_data:
            results = self.process_student_data(student_data)
            if results:
                return self.process_results(results)
        return None


class HomeworkCrawler(ABC):
    """作业爬虫接口

    定义作业爬虫的标准方法。
    子类需要实现具体的爬虫逻辑。
    """

    @abstractmethod
    def run(self) -> None:
        """运行作业爬虫

        执行完整的作业爬取流程。
        """
        pass

    @abstractmethod
    def login(self) -> bool:
        """执行登录操作

        Returns:
            bool: 登录是否成功
        """
        pass

    @abstractmethod
    def get_homework_grading_url(self, course_url: str) -> List[Dict[str, Any]]:
        """获取作业批阅链接列表

        Args:
            course_url: 课程页面URL

        Returns:
            List[Dict[str, Any]]: 作业批阅链接信息列表
        """
        pass

    @abstractmethod
    def process_homework(self, task: Dict[str, Any]) -> None:
        """处理单个作业

        Args:
            task: 作业任务信息
        """
        pass

    @abstractmethod
    def save_result(self, final_results: Dict[str, Any], task: Dict[str, Any]) -> None:
        """保存处理结果

        Args:
            final_results: 处理后的结果数据
            task: 任务信息，包含保存路径等数据
        """
        pass
