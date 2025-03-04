from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import LoginStrategy
from config.args import config
import time
import logging

class PasswordLoginStrategy(LoginStrategy):
    """密码登录策略类
    
    实现使用账号密码登录超星学习通的策略。
    """
    def login(self, driver: webdriver.Chrome) -> bool:
        try:
            # 等待页面加载完成
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="phone"]'))
            )

            # 输入手机号和密码
            driver.find_element(By.XPATH, '//*[@id="phone"]').send_keys(config.phonenumber)
            driver.find_element(By.XPATH, '//*[@id="pwd"]').send_keys(config.password)

            # 点击登录按钮
            driver.find_element(By.XPATH, '//*[@id="loginBtn"]').click()

            # 等待登录完成
            time.sleep(2)
            
            # 验证登录状态
            cookies = driver.get_cookies()
            return len(cookies) > 6
            
        except Exception as e:
            logging.error(f'账号密码登录失败：{str(e)}')
            return False

class QRCodeLoginStrategy(LoginStrategy):
    """二维码登录策略类
    
    实现使用二维码登录超星学习通的策略。
    """
    def login(self, driver: webdriver.Chrome) -> bool:
        try:
            # 等待二维码元素出现
            _ = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "quickCode"))
            )
            logging.info('请使用超星学习通APP扫描二维码登录')

            # 等待登录成功（通过检测URL变化判断）
            WebDriverWait(driver, 300).until(
                lambda driver: "passport2.chaoxing.com" not in driver.current_url
            )
            logging.info('扫码登录成功')
            
            # 验证登录状态
            cookies = driver.get_cookies()
            return len(cookies) > 6
            
        except Exception as e:
            logging.error(f'扫码登录失败：{str(e)}')
            return False

class LoginStrategyFactory:
    """登录策略工厂类
    
    用于创建不同的登录策略实例。
    """
    @staticmethod
    def create_strategy(use_qr_code: bool = False) -> LoginStrategy:
        """创建登录策略
        
        Args:
            use_qr_code: 是否使用二维码登录
            
        Returns:
            LoginStrategy: 登录策略实例
        """
        return QRCodeLoginStrategy() if use_qr_code else PasswordLoginStrategy()