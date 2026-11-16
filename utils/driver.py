"""A visible, temporary Chrome session managed by Selenium."""
def get_driver(headless=False):
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--window-size=1180,860')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    return driver
