import time
import json
import random
import undetected_chromedriver as uc
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.avito.ru/kaliningrad/kvartiry/sdam/posutochno/-ASgBAgICAkSSA8gQ8AeSUg?context=H4sIAAAAAAAA_wEjANz_YToxOntzOjg6ImZyb21QYWdlIjtzOjc6ImNhdGFsb2ciO312FITcIwAAAA"
OUTPUT_FILE = "avito_data.json"
DATA_DIR = 'data'
PAGES_MAX = 2

def get_random_sleep():
    return random.uniform(3, 6)

def parse_item(item):
    data = {
        "id": None,
        "title": None,
        "url": None,
        "price": None,
        "price_text": None,
        "rating": None,
        "reviews_count": None,
        "description": None,
        "seller_name": None,
        "seller_rating": None,
        "seller_reviews": None,
        "badges": []
    }

    try:
        data["id"] = item.get("data-item-id")

        title_link = item.find("a", attrs={"data-marker": "item-title"})
        if title_link:
            data["title"] = title_link.get("title")
            href = title_link.get("href")
            if href:
                data["url"] = "https://www.avito.ru" + href

        desc_meta = item.find("meta", attrs={"itemprop": "description"})
        if desc_meta:
            data["description"] = desc_meta.get("content")

        price_meta = item.find("meta", attrs={"itemprop": "price"})
        if price_meta:
            data["price"] = price_meta.get("content")
        
        price_tag = item.find("p", attrs={"data-marker": "item-price"})
        if price_tag:
            data["price_text"] = price_tag.get_text(strip=True).replace("\u00a0", " ")

        rating_block = item.find("div", attrs={"data-marker": "rating-and-reviews"})
        if rating_block:
            spans = rating_block.find_all("span")
            if spans:
                for span in spans:
                    text = span.get_text(strip=True)
                    if "," in text and len(text) <= 4:
                        data["rating"] = text
                    elif "отзыв" in text:
                        data["reviews_count"] = text

        seller_block = item.find("div", class_=lambda x: x and "iva-item-sellerInfo" in x)
        if seller_block:
            seller_link = seller_block.find("a", href=True)
            if seller_link:
                 name_p = seller_link.find("p") or seller_link.find("span")
                 if name_p:
                     data["seller_name"] = name_p.get_text(strip=True)
                 else:
                     data["seller_name"] = seller_link.get_text(strip=True)
            
            seller_score = seller_block.find("span", attrs={"data-marker": "seller-rating/score"})
            if seller_score:
                data["seller_rating"] = seller_score.get_text(strip=True)
            
            seller_summary = seller_block.find("p", attrs={"data-marker": "seller-info/summary"})
            if not seller_summary:
                 seller_summary = seller_block.find("span", attrs={"data-marker": "seller-info/summary"})
            
            if seller_summary:
                data["seller_reviews"] = seller_summary.get_text(strip=True)
        
        
        badges_elements = item.find_all("div", class_=lambda x: x and "SnippetBadge" in x)
        for badge in badges_elements:
            text_span = badge.find("span")
            if not text_span:
                content_div = badge.find("div", class_=lambda x: x and "content" in x.lower())
                if content_div:
                    data["badges"].append(content_div.get_text(strip=True))
                else:
                    text = badge.get_text(strip=True)
                    if text and len(text) < 30: 
                        data["badges"].append(text)
            else:
                data["badges"].append(text_span.get_text(strip=True))

        data["badges"] = list(set([b for b in data["badges"] if b]))

    except Exception as e:
        print(f"Error parsing item {data.get('id', 'unknown')}: {e}")

    return data

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    
    all_results = []

    try:
        for page in range(1, PAGES_MAX + 1):
            url = f"{BASE_URL}&p={page}"
            print(f"Текущая страница ({page}): {url}")
            
            driver.get(url)
            
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-marker="item"]'))
                )
            except:
                print("Ошибка ожидания")
                break

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            container = soup.find("div", attrs={"data-marker": "catalog-serp"})
            items = container.find_all("div", attrs={"data-marker": "item"})

            if not items:
                print("Нету объявлений(")
                break

            print(f"Всего {len(items)} объектов")

            for item_html in items:
                item_data = parse_item(item_html)
                if item_data["id"]:
                    all_results.append(item_data)

            time.sleep(get_random_sleep())

    except Exception as e:
        print(f"Что-то пошло не так: {e}")
    finally:
        driver.quit()

    with open(f'{DATA_DIR}/{OUTPUT_FILE}', "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
    
    print(f"Всё успешно сохранилось в {DATA_DIR}/{OUTPUT_FILE}")
    print(f'записей: {len(all_results)}')

if __name__ == "__main__":
    main()