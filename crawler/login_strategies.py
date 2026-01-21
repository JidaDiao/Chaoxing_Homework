from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .interface import LoginStrategy
from config._args import config
import time
import logging


class PasswordLoginStrategy(LoginStrategy):
    """密码登录策略类
    
    实现使用账号密码登录超星学习通的策略。
    通过提供账号和密码进行自动登录。
    """
    def __init__(self,config) -> None:
        self.config = config

    def login(self, driver: webdriver.Chrome, login_url: str) -> bool:
        """使用账号密码进行登录
        
        Args:
            driver: Chrome浏览器驱动实例
            login_url: 登录页面URL
            
        Returns:
            bool: 登录是否成功
        """
        try:
            # 打开登录页面
            driver.get(login_url)
            logging.info('正在打开超星学习通登录页面')
            
            # 等待页面加载完成，确保输入框可用
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="phone"]'))
            )
            logging.info('登录页面加载完成')

            # 输入手机号和密码
            phone_input = driver.find_element(By.XPATH, '//*[@id="phone"]')
            pwd_input = driver.find_element(By.XPATH, '//*[@id="pwd"]')
            
            phone_input.clear()  # 清除可能的默认值
            pwd_input.clear()
            
            phone_input.send_keys(self.config.phonenumber)
            pwd_input.send_keys(self.config.password)
            logging.info('已输入账号密码')

            # 点击登录按钮
            login_button = driver.find_element(By.XPATH, '//*[@id="loginBtn"]')
            login_button.click()
            logging.info('点击登录按钮')

            # 等待登录完成
            time.sleep(2)

            # 验证登录状态
            cookies = driver.get_cookies()
            login_success = len(cookies) > 6
            
            if login_success:
                logging.info('账号密码登录成功')
            else:
                logging.warning('账号密码登录可能失败，Cookie数量不足')
                
            return login_success

        except Exception as e:
            logging.error(f'账号密码登录失败：{str(e)}')
            return False


class QRCodeLoginStrategy(LoginStrategy):
    """二维码登录策略类
    
    实现使用二维码登录超星学习通的策略。
    需要用户手动扫描二维码完成登录。
    """
    def __init__(self,config) -> None:
        self.config = config

    def login(self, driver: webdriver.Chrome, login_url: str) -> bool:
        """使用二维码进行登录
        
        Args:
            driver: Chrome浏览器驱动实例
            login_url: 登录页面URL
            
        Returns:
            bool: 登录是否成功
        """
        try:
            # 打开登录页面
            driver.get(login_url)
            logging.info('正在打开超星学习通登录页面')
            
            # 等待二维码元素出现
            qr_code_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "quickCode"))
            )
            
            if qr_code_element:
                logging.info('二维码已加载，请使用超星学习通APP扫描二维码登录')
                logging.info('等待用户扫码登录，最长等待5分钟...')
                
                # 等待登录成功（通过检测URL变化判断）
                WebDriverWait(driver, 300).until(
                    lambda driver: "passport2.chaoxing.com" not in driver.current_url
                )
                logging.info('检测到URL变化，扫码登录成功')

                # 验证登录状态
                cookies = driver.get_cookies()
                login_success = len(cookies) > 6
                
                if login_success:
                    logging.info('二维码登录成功确认')
                else:
                    logging.warning('二维码登录可能失败，Cookie数量不足')
                    
                return login_success
            else:
                logging.error('未能加载二维码元素')
                return False

        except Exception as e:
            logging.error(f'二维码登录失败：{str(e)}')
            return False


class LoginStrategyFactory:
    """登录策略工厂类
    
    用于创建不同的登录策略实例。
    根据配置选择合适的登录方式。
    """
    
    @staticmethod
    def create_strategy(use_qr_code: bool = False,config = config) -> LoginStrategy:
        """创建登录策略
        
        Args:
            use_qr_code: 是否使用二维码登录
            
        Returns:
            LoginStrategy: 登录策略实例
        """
        if use_qr_code:
            logging.info('使用二维码登录策略')
            return QRCodeLoginStrategy(config)
        else:
            logging.info('使用账号密码登录策略')
            return PasswordLoginStrategy(config)
