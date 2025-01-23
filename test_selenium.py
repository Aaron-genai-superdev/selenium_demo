from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# 设置 ChromeDriver 服务
service = Service('/usr/local/bin/chromedriver')

# 配置选项
options = Options()
options.add_argument("--user-data-dir=/tmp/chrome_user_data")  # 指定一个唯一的用户数据目录
options.add_argument("--headless")  # 可选：如果你在无界面服务器上运行，添加此参数
options.add_argument("--no-sandbox")  # 可选：在某些环境中需要此参数
options.add_argument("--disable-dev-shm-usage")  # 可选：避免共享内存问题

# 初始化 WebDriver
driver = webdriver.Chrome(service=service, options=options)

# 测试打开 Google
driver.get("https://www.google.com")
print("Page title is:", driver.title)

# 关闭浏览器
driver.quit()
