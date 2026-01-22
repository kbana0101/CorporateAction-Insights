from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from pathlib import Path
from typing import List
import time
import os


def crawl_bse_corporate_actions(
    output_dir: str = "xbrl_files",
) -> List[str]:
    """
    Crawls BSE corporate action data and stores raw XML/XBRL files.

    Returns:
        List of file paths of downloaded XML files
    """

    # Setup WebDriver (Chrome here)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in background
    driver = webdriver.Chrome(options=options)

    try:
        url = "https://www.bseindia.com/corporates/ann.html"
        driver.get(url)

        today = datetime.today().strftime("%d/%m/%Y")

        driver.execute_script("document.getElementById('txtFromDt').value = arguments[0];", today)
        driver.execute_script("document.getElementById('txtToDt').value = arguments[0];", today)
        driver.execute_script("document.getElementById('txtToDt').dispatchEvent(new Event('blur'));")

        category = Select(driver.find_element(By.ID, "ddlPeriod"))

        submit_btn = driver.find_element(By.ID, "btnSubmit")
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        time.sleep(1)
        submit_btn.click()

        time.sleep(4)

        page_no = 1
        while True:
            print(f"📄 Scraping page {page_no}...")

            # Scrape XBRL links on this page
            xbrl_buttons = driver.find_elements(By.XPATH, "//a[normalize-space(text())='XBRL']")

            if not xbrl_buttons:
                print("⚠ No XBRL links found on this page.")

            os.makedirs(output_dir, exist_ok=True)
            downloaded_files: list[str] = []

            for idx, btn in enumerate(xbrl_buttons, start=1):
                try:
                    if btn.get_attribute("href"):
                        continue

                    main_window = driver.current_window_handle
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)

                    windows = driver.window_handles
                    new_window = [w for w in windows if w != main_window][0]
                    driver.switch_to.window(new_window)

                    xml_content = driver.page_source
                    filename = f"xbrl_p{page_no}_{idx}.xml"
                    with open(os.path.join("xbrl_files", filename), "w", encoding="utf-8") as f:
                        f.write(xml_content)

                    print(f"✅ Saved {filename}")

                    driver.close()
                    driver.switch_to.window(main_window)
                    time.sleep(1)

                except Exception as e:
                    print(f"❌ Failed at button {idx} on page {page_no} -> {e}")

            # ==== PAGINATION SECTION (NEW CODE) ====

            try:


                try:
                    next_btn = driver.find_element(By.ID, "idnext")
                except:
                    print("✔ No Next button found (final page). Finished scraping.")
                    break

                # Check if disabled by CSS (pointer-events:none)
                style = next_btn.get_attribute("style") or ""
                if "pointer-events: none" in style or "disabled" in style.lower():
                    print("✔ No more pages. Finished scraping.")
                    break

                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(1)
                next_btn.click()

                time.sleep(4)
                page_no += 1

            except Exception as e:
                print(f"✔ No next button found. Ending. {e}")
                break

    finally:
        driver.quit()
    return downloaded_files

files = crawl_bse_corporate_actions()
print(len(files))
print(files[:3])

