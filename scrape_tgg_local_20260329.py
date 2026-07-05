import time
import re
import os
import sys
import traceback
import pandas as pd
from datetime import datetime, timezone

import boto3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# ===== 配置 =====
BUCKET = os.getenv("BUCKET", "fridge-tgg-scrape-bucket")
PROCESSED_PREFIX = os.getenv("PROCESSED_PREFIX", "processed/")
HEADLESS = os.getenv("HEADLESS", "1") == "1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(SCRIPT_DIR, "task_run.log")

URL = "https://www.thegoodguys.com.au/fridges-and-freezers/refrigerators"

s3 = boto3.client("s3")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def close_popup(driver):
    try:
        btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='dialog-close']"))
        )
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)
    except:
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except:
            pass


def click_load_more(driver):
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Load more']]"))
        )
        driver.execute_script("arguments[0].click();", btn)
        return True
    except:
        return False


def extract_brand(title):
    return title.split()[0] if title else ""


def clean_price(price):
    return int(re.sub(r"[^\d]", "", price)) if price else None


def extract_rating(card):
    try:
        raw = card.find_element(By.CSS_SELECTOR, "span[role='img']").get_attribute("aria-label")
        return float(re.findall(r"\d+\.?\d*", raw)[0])
    except:
        return None


def main():

    run_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    log("=== START TGG SCRAPER ===")

    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(URL)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid^='product-card-']"))
        )

        close_popup(driver)

        # Load more
        while True:
            close_popup(driver)
            if not click_load_more(driver):
                break
            time.sleep(2)

        cards = driver.find_elements(By.CSS_SELECTOR, "div[data-testid^='product-card-']")

        products = []

        for c in cards:
            try:
                title = c.find_element(By.TAG_NAME, "h4").text.strip()
                model = c.find_element(By.CSS_SELECTOR, "p[class*='modelNumber']").text.strip()
                price = c.find_element(By.CSS_SELECTOR, "span[data-testid='product-card-price-section-price']").text.strip()
            except:
                continue

            if not title or not price:
                continue

            products.append({
                "date": run_dt,
                "retailer": "TGG",
                "brand": extract_brand(title),
                "title": title,
                "model": model,
                "price_text": price,
                "price": clean_price(price),
                "rating": extract_rating(c)
            })

        df = pd.DataFrame(products).drop_duplicates()

        log(f"rows={len(df)}")

        # 本地文件
        filename = f"tgg_fridges_{timestamp}.csv"
        local_path = os.path.join(SCRIPT_DIR, filename)

        df.to_csv(local_path, index=False, encoding="utf-8-sig")

        # 上传 S3（仅 processed）
        key = f"{PROCESSED_PREFIX}dt={run_dt}/{filename}"

        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=df.to_csv(index=False).encode("utf-8")
        )

        log(f"uploaded: s3://{BUCKET}/{key}")

        return 0

    except Exception as e:
        log("ERROR")
        log(repr(e))
        log(traceback.format_exc())
        return 99

    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())