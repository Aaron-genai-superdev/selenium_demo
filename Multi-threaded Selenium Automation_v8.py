"""
MLion.AI 自动化任务脚本
------------------------
最后更新: 2025-01-14
作者: Aaron Zhang

功能概述:
--------
自动化执行MLion.AI平台的日常任务，包括签到和新闻分享，以获取平台积分。

主要功能:
--------
1. 自动登录
2. 每日签到 (+500积分)
3. 新闻分享 (+3000积分)
   - 支持微信、推特、脸书、微博等平台
   - 每个平台分享多次
4. 积分追踪
   - 记录初始积分
   - 追踪签到后积分
   - 统计分享获得积分
   - 计算总收益

关键类和方法:
-----------
AutomationWorker类:
- setup_driver(): 初始化Chrome浏览器
- login(): 执行登录流程
- get_points(): 获取当前积分
- navigate_to_points_center(): 导航到积分中心
- do_check_in(): 执行签到操作
- navigate_to_news(): 导航到新闻页面
- handle_social_media_sharing(): 执行社交媒体分享
- click_share_button(): 点击分享按钮
- close_dialog(): 关闭弹窗广告
- wait_and_click(): 等待元素可点击并执行点击
- wait_for_element(): 等待元素出现
- random_delay(): 添加随机延时

错误处理:
--------
- 所有关键操作都有重试机制
- 完整的错误日志记录
- 异常捕获和处理
- 调试信息保存（截图和页面源码）

使用方法:
--------
1. 设置环境变量 MLION_ACCOUNTS:
   {
     "username": "your_email@example.com",
     "password": "your_password"
   }

2. 确保 ChromeDriver 已安装在 /usr/local/bin/chromedriver

更新历史:
--------
2025-01-14:
- 增加签到功能
- 优化积分统计逻辑
- 添加分享任务完成后的延时等待
- 实现多次重试获取最新积分机制

"""

import os
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import logging
import random
import json
from dotenv import load_dotenv
import atexit

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)

# 加载环境变量
load_dotenv()


class AutomationWorker:
    def __init__(self, account_info):
        self.username = account_info['username']
        self.password = account_info['password']
        self.driver = None
        self.logger = logging.getLogger(f'Worker-{self.username}')
        # 为每个账号生成一个唯一的 user-data-dir 路径
        self.user_data_dir = f"/tmp/chrome_user_data_{uuid.uuid4()}"
        atexit.register(self.cleanup)  # 注册退出时的清理操作
    def setup_driver(self):
        """初始化 ChromeDriver"""
        service = Service("/usr/local/bin/chromedriver")
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.user_data_dir}")  # 唯一的用户数据目录
        options.add_argument("--headless")  # 无界面模式
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.maximize_window()
        self.logger.info("浏览器初始化完成")
        self.logger.info(f"为账号 {self.username} 设置了用户数据目录: {self.user_data_dir}")
    def cleanup(self):
        """清理临时的用户数据目录"""
        try:
            if os.path.exists(self.user_data_dir):
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
                self.logger.info(f"已删除临时目录: {self.user_data_dir}")
        except Exception as e:
            self.logger.error(f"清理用户数据目录失败: {e}")
    def random_delay(self, min_seconds=1, max_seconds=3):
        """添加随机延时"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return delay

    def setup_driver(self):
        """初始化 ChromeDriver"""
        service = Service("/usr/local/bin/chromedriver")
        self.driver = webdriver.Chrome(service=service)
        self.driver.maximize_window()
        self.logger.info("浏览器初始化完成")

    def save_debug_info(self, step_name):
        """保存页面截图和部分页面源代码"""
        try:
            screenshot_filename = f"{self.username}_{step_name}_screenshot.png"
            html_filename = f"{self.username}_{step_name}_page_source.html"
            self.driver.save_screenshot(screenshot_filename)
            self.logger.info(f"已保存截图：{screenshot_filename}")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            self.logger.info(f"已保存页面源代码：{html_filename}")
        except Exception as e:
            self.logger.error(f"保存调试信息失败：{e}")

    def close_dialog(self, timeout=10):
        """关闭任何可见的对话框"""
        try:
            close_button_selectors = [
                "svg.icon.close-img",
                "svg.icon.close",
                ".el-dialog__close",
                "button.el-dialog__headerbtn",
                ".close-button",
                "[aria-label='Close']"
            ]

            for selector in close_button_selectors:
                try:
                    close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in close_buttons:
                        if button.is_displayed():
                            button.click()
                            self.random_delay()
                            self.logger.info(f"成功点击关闭按钮: {selector}")
                            return True
                except:
                    continue
            return False
        except Exception as e:
            self.logger.error(f"关闭对话框时出错: {e}")
            return False

    def wait_and_click(self, locator, timeout=10, retries=3, sleep_between_retries=2):
        """等待元素可点击并进行点击，带重试机制"""
        for attempt in range(retries):
            try:
                self.close_dialog()
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable(locator)
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                self.random_delay()
                self.close_dialog()
                element.click()
                return True
            except Exception as e:
                self.logger.warning(f"点击失败，第 {attempt + 1} 次尝试: {e}")
                if attempt < retries - 1:
                    time.sleep(sleep_between_retries)
        return False

    def wait_for_element(self, locator, timeout=10, retries=3):
        """等待元素出现，带重试机制"""
        for attempt in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located(locator)
                )
                return element
            except Exception as e:
                self.logger.warning(f"等待元素失败，第 {attempt + 1} 次尝试: {e}")
                if attempt < retries - 1:
                    self.random_delay()
                    self.close_dialog()
        return None

    def wait_for_page_load(self, text_marker, timeout=10):
        """等待页面加载完成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if text_marker in self.driver.page_source:
                return True
            time.sleep(1)
        return False

    def login(self):
        """执行登录流程"""
        self.logger.info("开始登录流程")
        if self.close_dialog():
            self.logger.info("成功关闭初始弹窗")

        sign_in_locators = [
            (By.XPATH, "//div[contains(., 'Sign in') and contains(@class, 'baseFontColor left')]"),
            (By.CSS_SELECTOR, ".baseFontColor.left"),
            (By.LINK_TEXT, "Sign in"),
            (By.PARTIAL_LINK_TEXT, "Sign")
        ]

        for locator in sign_in_locators:
            if self.wait_and_click(locator):
                self.logger.info("成功点击 'Sign in' 按钮")
                self.random_delay(2, 3)

                username_input = self.wait_for_element((By.XPATH, "//input[@placeholder='Email']"))
                password_input = self.wait_for_element((By.XPATH, "//input[@placeholder='Password']"))

                if username_input and password_input:
                    username_input.send_keys(self.username)
                    password_input.send_keys(self.password)
                    self.logger.info("用户名和密码已输入")

                    if self.wait_and_click((By.XPATH, "//button[span[text()='Login']]")):
                        self.logger.info("成功提交登录信息")
                        self.random_delay(4, 6)
                        return True

        return False

    def get_points(self):
        """获取当前积分"""
        try:
            point_element = self.wait_for_element(
                (By.CSS_SELECTOR, "div.pointDisplay.greenColor div.text"),
                timeout=10
            )
            if point_element and point_element.is_displayed():
                points = point_element.text.strip()
                points = points.replace(',', '')
                if points.isdigit():
                    self.logger.info(f"当前积分：{points}")
                    return points

            point_element = self.wait_for_element(
                (By.XPATH, "//div[contains(@class, 'pointDisplay')]//div[contains(@class, 'text')]"),
                timeout=5
            )
            if point_element and point_element.is_displayed():
                points = point_element.text.strip().replace(',', '')
                if points.isdigit():
                    self.logger.info(f"当前积分：{points}")
                    return points

            self.logger.warning("未能找到积分元素")
            return "0"

        except Exception as e:
            self.logger.error(f"获取积分失败: {e}")
            return "0"

    def navigate_to_points_center(self):
        """导航到积分中心页面"""
        self.logger.info("=== 导航到积分中心页面 ===")
        self.driver.get("https://www.mlion.ai/#/pointsCenter/")
        self.random_delay(4, 6)

        if self.close_dialog():
            self.logger.info("成功关闭积分中心页面上的广告弹窗")
        return True

    def do_check_in(self):
        """执行签到操作，处理已签到的情况"""
        self.logger.info("=== 开始执行签到操作 ===")
        try:
            # 首先检查是否已经签到
            already_checked_elements = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'rightBtn')]//div[contains(text(), 'Checked') or contains(text(), 'checked')]"
            )

            if already_checked_elements and any(elem.is_displayed() for elem in already_checked_elements):
                self.logger.info("今日已经完成签到，继续执行其他任务")
                return "already_checked"

            check_in_locators = [
                (By.XPATH,
                 "//div[contains(@class, 'rightBtn')]//div[contains(@class, 'centerBtn') and contains(text(), 'Check In')]"),
                (By.CSS_SELECTOR, "div[data-v-7fb00e4c].rightBtn div.centerBtn"),
                (By.XPATH, "//div[contains(text(), 'Check In')]")
            ]

            for locator in check_in_locators:
                if self.wait_and_click(locator, timeout=10, retries=3):
                    self.logger.info("成功点击签到按钮")
                    self.random_delay(3, 5)
                    return "success"

            self.logger.warning("未找到签到按钮或签到按钮不可点击")
            return "not_found"

        except Exception as e:
            self.logger.error(f"签到过程出错: {e}")
            self.save_debug_info("check_in_failure")
            return "error"

    def navigate_to_news(self):
        """导航到新闻页面"""
        self.logger.info("=== 导航到新闻页面 ===")
        self.driver.get("https://mlion.ai/#/message/news")
        self.random_delay(4, 6)

        if self.wait_for_page_load("Weekly News Highlights", 10):
            self.logger.info("成功加载 News 页面")
            if self.close_dialog():
                self.logger.info("成功关闭 News 页面上的广告弹窗")
            return True
        return False

    def ensure_share_dialog_open(self):
        """确保分享弹窗是打开的"""
        try:
            dialog = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-v-8acae2bc]"))
            )

            if not dialog.is_displayed():
                share_buttons = self.driver.find_elements(By.CLASS_NAME, "shareBox")
                if len(share_buttons) > 1:
                    share_buttons[1].click()
                    self.random_delay(2, 4)

            return dialog.is_displayed()
        except Exception as e:
            self.logger.error(f"确保分享弹窗打开时出错: {e}")
            return False

    def handle_social_media_sharing(self, max_attempts=10):
        """处理社交媒体分享流程"""
        social_media_selectors = [
            ("div.linkImg.wx.el-tooltip__trigger", "WeChat"),
            ("div.linkImg div:contains('twitter')", "Twitter"),
            ("div.linkImg div:contains('facebook')", "Facebook"),
            ("div.linkImg div:contains('weibo')", "Weibo")
        ]

        successful_clicks = 0

        for i in range(max_attempts):
            platform = social_media_selectors[i % 4]
            self.logger.info(f"=== 开始第 {i + 1} 次社交媒体分享尝试 ===")

            if not self.ensure_share_dialog_open():
                self.logger.info("尝试重新打开分享弹窗")
                try:
                    share_buttons = self.driver.find_elements(By.CLASS_NAME, "shareBox")
                    if len(share_buttons) > 1:
                        share_buttons[1].click()
                        self.random_delay(2, 4)
                except:
                    self.logger.warning("重新打开分享弹窗失败，继续尝试")

            try:
                if platform[1] == "WeChat":
                    xpath = "//div[contains(@class, 'linkImg') and contains(@class, 'wx')]"
                else:
                    xpath = f"//div[contains(@class, 'linkImg')]/div[normalize-space(text())='{platform[1].lower()}']/.."

                buttons = self.driver.find_elements(By.XPATH, xpath)
                if buttons:
                    for button in buttons:
                        if button.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            self.random_delay()

                            try:
                                button.click()
                                self.logger.info(f"成功点击 '{platform[1]}' 按钮！第 {i + 1} 次")
                                successful_clicks += 1
                                self.random_delay(2, 4)
                                break
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", button)
                                    self.logger.info(f"通过 JavaScript 成功点击 '{platform[1]}' 按钮！第 {i + 1} 次")
                                    successful_clicks += 1
                                    self.random_delay(2, 4)
                                    break
                                except Exception as e:
                                    self.logger.error(f"JavaScript 点击 {platform[1]} 按钮失败: {e}")
                    else:
                        self.logger.warning(f"找到了 {platform[1]} 按钮但无法点击")
                else:
                    self.logger.warning(f"未找到 {platform[1]} 按钮")

            except Exception as e:
                self.logger.error(f"处理 {platform[1]} 按钮时出错: {e}")
                self.save_debug_info(f"social_media_click_failure_{platform[1]}")

            self.random_delay(2, 4)

        return successful_clicks

    def click_share_button(self, max_retries=5):
        """点击分享按钮，带重试机制"""
        self.logger.info("=== 点击分享按钮 ===")

        for attempt in range(max_retries):
            try:
                share_button_locators = [
                    (By.CLASS_NAME, "shareBox"),
                    (By.CSS_SELECTOR, ".shareBox"),
                    (By.XPATH, "//div[contains(@class, 'shareBox')]"),
                    (By.CSS_SELECTOR, "[class*='shareBox']")
                ]

                for locator in share_button_locators:
                    try:
                        share_buttons = self.driver.find_elements(*locator)
                        if share_buttons and len(share_buttons) > 1:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", share_buttons[1])
                            self.random_delay()

                            try:
                                share_buttons[1].click()
                                self.logger.info(f"成功点击 Share 按钮（第 {attempt + 1} 次尝试）")
                                return True
                            except:
                                self.driver.execute_script("arguments[0].click();", share_buttons[1])
                                self.logger.info(f"通过 JavaScript 成功点击 Share 按钮（第 {attempt + 1} 次尝试）")
                                return True
                    except Exception as e:
                        self.logger.warning(f"使用定位器 {locator} 查找 Share 按钮失败: {e}")
                        continue

                if attempt < max_retries - 1:
                    self.logger.warning(f"第 {attempt + 1} 次尝试未找到 Share 按钮，刷新页面重试...")
                    self.driver.refresh()
                    self.random_delay(4, 6)

                    if self.close_dialog():
                        self.logger.info("刷新后关闭弹窗成功")

                    if self.wait_for_page_load("Weekly News Highlights", 10):
                        self.logger.info("页面刷新完成，继续查找 Share 按钮")
                    else:
                        self.logger.warning("页面刷新后未找到预期内容")

            except Exception as e:
                self.logger.error(f"尝试点击 Share 按钮时出错 (尝试 {attempt + 1}/{max_retries}): {e}")
                self.save_debug_info(f"share_button_click_failure_{attempt}")
                if attempt < max_retries - 1:
                    self.random_delay(2, 4)

        self.logger.error("经过多次尝试后仍未找到 Share 按钮")
        return False

    def run_automation(self):
        """运行自动化流程"""
        try:
            self.setup_driver()
            self.driver.get("https://www.mlion.ai")
            self.logger.info("成功打开网站")
            self.random_delay(4, 6)

            if self.login():
                self.logger.info("登录成功")

                # 获取初始积分
                initial_points = self.get_points()
                self.logger.info(f"账号 {self.username} 开始任务时积分：{initial_points}")

                # 进行签到
                if self.navigate_to_points_center():
                    check_in_result = self.do_check_in()

                    if check_in_result in ["success", "already_checked"]:
                        if check_in_result == "success":
                            self.logger.info("签到成功，等待积分更新...")
                            self.random_delay(3, 5)

                            # 签到后直接返回主页面查看积分
                            self.driver.get("https://www.mlion.ai/#/")
                            self.random_delay(4, 6)

                            # 获取签到后的积分
                            after_checkin_points = self.get_points()
                            checkin_points_earned = int(after_checkin_points) - int(
                                initial_points) if after_checkin_points.isdigit() and initial_points.isdigit() else 0

                            print(f"\n=== 签到完成报告 ===")
                            print(f"账号: {self.username}")
                            print(f"初始积分: {initial_points}")
                            print(f"签到后积分: {after_checkin_points}")
                            print(f"签到获得积分: {checkin_points_earned}")
                            print("===================\n")
                        else:  # already_checked
                            self.logger.info("今日已签到，继续执行其他任务")
                            after_checkin_points = initial_points
                            checkin_points_earned = 0

                        # 继续进行分享任务
                        if self.navigate_to_news():
                            max_overall_attempts = 3
                            for overall_attempt in range(max_overall_attempts):
                                if self.click_share_button():
                                    successful_clicks = self.handle_social_media_sharing()
                                    self.logger.info(f"社交媒体分享完成，成功次数：{successful_clicks}/10")
                                    break
                                else:
                                    if overall_attempt < max_overall_attempts - 1:
                                        self.logger.warning(
                                            f"第 {overall_attempt + 1} 次整体尝试失败，将重试整个分享流程...")
                                        self.random_delay(4, 6)
                                    else:
                                        self.logger.error("达到最大重试次数，程序结束")

                            # 分享任务完成后，等待较长时间让积分同步
                            self.logger.info("分享任务完成，等待积分同步...")
                            self.random_delay(10, 15)

                            # 返回主页面查看最终积分
                            self.driver.get("https://www.mlion.ai/#/")
                            self.random_delay(4, 6)

                            # 获取最终积分（尝试多次以确保获取到更新后的积分）
                            max_retries = 3
                            final_points = after_checkin_points
                            for retry in range(max_retries):
                                current_points = self.get_points()
                                if current_points != after_checkin_points:  # 如果积分有变化
                                    final_points = current_points
                                    break
                                if retry < max_retries - 1:
                                    self.logger.info("积分可能还未更新，等待后重试...")
                                    self.random_delay(5, 8)
                                    self.driver.refresh()
                                    self.random_delay(3, 5)

                            if final_points.isdigit() and after_checkin_points.isdigit():
                                sharing_points_earned = int(final_points) - int(after_checkin_points)
                                total_points_earned = int(final_points) - int(initial_points)

                                print(f"\n=== 任务完成总报告 ===")
                                print(f"账号: {self.username}")
                                print(f"初始积分: {initial_points}")
                                print(f"签到后积分: {after_checkin_points}")
                                print(f"最终积分: {final_points}")
                                print(f"签到获得积分: {checkin_points_earned}")
                                print(f"分享获得积分: {sharing_points_earned}")
                                print(f"总共获得积分: {total_points_earned}")
                                print("===================\n")
                        else:
                            self.logger.error("无法导航到新闻页面")
                    else:
                        self.logger.error(f"签到过程异常: {check_in_result}")
                else:
                    self.logger.error("无法导航到积分中心页面")
            else:
                self.logger.error("登录失败")

        except Exception as e:
            self.logger.error(f"自动化过程出错: {e}")
            self.save_debug_info("general_failure")
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("浏览器已关闭")
            self.cleanup()  # 清理临时数据

def load_accounts():
    """从环境变量加载账户信息"""
    accounts_json = os.getenv('MLION_ACCOUNTS')
    if not accounts_json:
        raise ValueError("未找到账户配置信息，请设置 MLION_ACCOUNTS 环境变量")

    try:
        return json.loads(accounts_json)
    except json.JSONDecodeError:
        raise ValueError("账户配置信息格式错误，请确保是有效的 JSON 格式")


def main():
    # 加载账户信息
    try:
        accounts = load_accounts()
        logging.info(f"成功加载 {len(accounts)} 个账户")
    except Exception as e:
        logging.error(f"加载账户信息失败: {e}")
        return

    # 顺序执行每个账号
    for account in accounts:
        try:
            worker = AutomationWorker(account)
            # 账号之间添加随机延迟
            if accounts.index(account) > 0:
                delay = random.uniform(10, 20)
                logging.info(f"账号 {account['username']} 将在 {delay:.2f} 秒后启动")
                time.sleep(delay)

            worker.run_automation()

            # 账号执行完成后添加额外延迟
            delay = random.uniform(5, 10)
            logging.info(f"账号 {account['username']} 执行完成，等待 {delay:.2f} 秒后启动下一个账号")
            time.sleep(delay)

        except Exception as e:
            logging.error(f"账号 {account['username']} 执行失败: {e}")
            continue

    logging.info("所有账户的自动化任务已完成")


if __name__ == "__main__":
    main()