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
    return random.uniform(3, 5)

def clean_text(text):
    if text:
        return text.strip().replace("\u00a0", " ")
    return None

def save_data(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
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
        raw_id = item.get("data-item-id")
        if raw_id:
            data["id"] = raw_id.strip()

        title_link = item.find("a", attrs={"data-marker": "item-title"})
        if title_link:
            data["title"] = clean_text(title_link.get("title"))
            href = title_link.get("href")
            if href:
                data["url"] = "https://www.avito.ru" + href

        desc_meta = item.find("meta", attrs={"itemprop": "description"})
        if desc_meta:
            data["description"] = clean_text(desc_meta.get("content"))

        price_meta = item.find("meta", attrs={"itemprop": "price"})
        if price_meta:
            data["price"] = clean_text(price_meta.get("content"))
        
        price_tag = item.find("p", attrs={"data-marker": "item-price"})
        if price_tag:
            data["price_text"] = clean_text(price_tag.get_text(strip=True))

        rating_block = item.find("div", attrs={"data-marker": "rating-and-reviews"})
        if rating_block:
            spans = rating_block.find_all("span")
            if spans:
                for span in spans:
                    text = clean_text(span.get_text(strip=True))
                    if not text:
                        continue
                    
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
                     data["seller_name"] = clean_text(name_p.get_text(strip=True))
                 else:
                     data["seller_name"] = clean_text(seller_link.get_text(strip=True))
            
            seller_score = seller_block.find("span", attrs={"data-marker": "seller-rating/score"})
            if seller_score:
                data["seller_rating"] = clean_text(seller_score.get_text(strip=True))
            
            seller_summary = seller_block.find("p", attrs={"data-marker": "seller-info/summary"})
            if not seller_summary:
                 seller_summary = seller_block.find("span", attrs={"data-marker": "seller-info/summary"})
            
            if seller_summary:
                data["seller_reviews"] = clean_text(seller_summary.get_text(strip=True))
        
        badges_elements = item.find_all("div", class_=lambda x: x and "SnippetBadge" in x)
        for badge in badges_elements:
            val_to_add = None
            text_span = badge.find("span")
            
            if not text_span:
                content_div = badge.find("div", class_=lambda x: x and "content" in x.lower())
                if content_div:
                    val_to_add = clean_text(content_div.get_text(strip=True))
                else:
                    raw_text = badge.get_text(strip=True)
                    if raw_text and len(raw_text) < 30: 
                        val_to_add = clean_text(raw_text)
            else:
                val_to_add = clean_text(text_span.get_text(strip=True))
            
            if val_to_add:
                data["badges"].append(val_to_add)

    except Exception as e:
        print(f"Ошибка при парсинге элемента: {e}")

    return data

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    output_path = f'{DATA_DIR}/{OUTPUT_FILE}'
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    
    all_results = []

    try:
        for page in range(1, PAGES_MAX + 1):
            url = f"{BASE_URL}&p={page}"
            print(f"Текущая страница ({page}): {url}")
            
            driver.get(url)
            
            try: # Интересное замечание, этот код неплохой такой captcha чекер
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-marker="item"]'))
                )
            except:
                print("Ошибка ожидания")
                break
            
            time.sleep(2)
               
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            container = soup.find("div", attrs={"data-marker": "catalog-serp"})
            if not container:
                print("Не найден контейнер объявлений")
                break
                
            items = container.find_all("div", attrs={"data-marker": "item"})

            if not items:
                print("Нет объявлений на странице")
                break

            print(f"Всего {len(items)} объектов на странице")

            for item_html in items:
                item_data = parse_item(item_html)
                if item_data["id"]:
                    all_results.append(item_data)

            time.sleep(get_random_sleep())

    except Exception as e:
        print(f"Что-то пошло не так: {e}")
    finally:
        driver.quit()

    save_data(all_results, output_path)
    
    print(f"Всё успешно сохранилось в {output_path}")
    print(f'Всего записей: {len(all_results)}')

if __name__ == "__main__":
    main()