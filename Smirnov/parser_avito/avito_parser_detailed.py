import time
import json
import random
import undetected_chromedriver as uc
import os
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

INPUT_FILE = "avito_data.json"
OUTPUT_FILE = "avito_details.json"
DATA_DIR = 'data'

def get_random_sleep():
    return random.uniform(3, 5)

def clean_text(text):
    if text:
        return text.strip().replace("\u00a0", " ")
    return None

def save_data(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def parse_detailed_page(soup, url):
    data = {
        "id": None,
        "title": None,
        "url": url,
        "price": None,
        "price_text": None,
        "rating": None,
        "reviews_count": None,
        "description": None,
        "seller_name": None,
        "seller_rating": None,
        "seller_reviews": None,
        "badges": [],
        "parsed_at": datetime.now().isoformat(),
        "about_apartment": {},
        "rules": {},
        "location": {
            "address": None,
            "district": None,
            "lat": None,
            "lon": None
        },
        "about_building": {},
        "meta": {
            "id": None,
            "published_date": None,
            "total_views": None,
            "today_views": None
        }
    }

    try:
        item_id_elem = soup.find("span", attrs={"data-marker": "item-view/item-id"})
        if item_id_elem:
            data["id"] = clean_text(item_id_elem.get_text(strip=True)).replace("№ ", "")
            data["meta"]["id"] = data["id"]

        title_elem = soup.find("h1", attrs={"data-marker": "item-view/title-info"})
        if title_elem:
            data["title"] = clean_text(title_elem.get_text(strip=True))

        price_meta = soup.find("span", attrs={"itemprop": "price"})
        if price_meta:
            data["price"] = price_meta.get("content")

        price_container = soup.find("div", attrs={"data-marker": "item-view/item-price-container"})
        if price_container:
            data["price_text"] = clean_text(price_container.get_text(separator=" ", strip=True))

        desc_elem = soup.find("div", attrs={"data-marker": "item-view/item-description"})
        if desc_elem:
            data["description"] = desc_elem.get_text("\n", strip=True)

        rating_badge = soup.find("div", attrs={"data-marker": "item-navigation/rating-badge"})
        if rating_badge:
            spans = rating_badge.find_all("span")
            for span in spans:
                text = clean_text(span.get_text(strip=True))
                if not text:
                    continue
                
                if "отзыв" in text.lower():
                    data["reviews_count"] = text
                elif len(text) <= 5 and ("," in text or "." in text):
                    data["rating"] = text

        seller_block = soup.find("div", attrs={"data-marker": "item-view/seller-info"})
        if seller_block:
            name_elem = seller_block.find("div", attrs={"data-marker": "seller-info/name"})
            if name_elem:
                data["seller_name"] = clean_text(name_elem.get_text(strip=True))
            
            seller_rating_elem = seller_block.find("span", class_=lambda x: x and "seller-info-rating-score" in x)
            if seller_rating_elem:
                data["seller_rating"] = clean_text(seller_rating_elem.get_text(strip=True))

            seller_reviews_elem = seller_block.find("a", attrs={"data-marker": "rating-caption/rating"})
            if seller_reviews_elem:
                data["seller_reviews"] = clean_text(seller_reviews_elem.get_text(strip=True))
        
        badges_container = soup.find("div", class_=lambda x: x and "style__item-view-badge-bar" in x)
        if badges_container:
            badges = badges_container.find_all("div", class_=lambda x: x and "CardBadge__title" in x)
            for b in badges:
                data["badges"].append(clean_text(b.get_text(strip=True)))

        params_blocks = soup.find_all("div", attrs={"data-marker": "item-view/item-params"})
        
        for block in params_blocks:
            header = block.find("h2")
            if not header:
                continue
            
            header_text = header.get_text(strip=True)
            items_list = block.find("ul")
            if not items_list:
                continue
            
            items = items_list.find_all("li")
            current_dict = {}
            
            for item in items:
                spans = item.find_all("span")
                if len(spans) > 0:
                    key = clean_text(spans[0].get_text(strip=True)).rstrip(":")
                    full_text = clean_text(item.get_text(strip=True))
                    value = full_text.replace(key + ":", "").strip()
                    current_dict[key] = value

            if "О квартире" in header_text:
                data["about_apartment"] = current_dict
            elif "Правила" in header_text:
                data["rules"] = current_dict
            elif "О доме" in header_text:
                data["about_building"] = current_dict

        map_wrapper = soup.find("div", attrs={"data-marker": "item-map-wrapper"})
        if map_wrapper:
            data["location"]["lat"] = map_wrapper.get("data-map-lat")
            data["location"]["lon"] = map_wrapper.get("data-map-lon")
        
        address_elem = soup.find("span", class_=lambda x: x and "style__item-address__string" in x)
        if address_elem:
             data["location"]["address"] = clean_text(address_elem.get_text(strip=True))
        
        district_elem = soup.find("span", class_=lambda x: x and "style__item-address-georeferences-item" in x)
        if district_elem:
            data["location"]["district"] = clean_text(district_elem.get_text(strip=True))

        date_elem = soup.find("span", attrs={"data-marker": "item-view/item-date"})
        if date_elem:
            data["meta"]["published_date"] = clean_text(date_elem.get_text(strip=True))
        
        total_views_elem = soup.find("span", attrs={"data-marker": "item-view/total-views"})
        if total_views_elem:
            data["meta"]["total_views"] = clean_text(total_views_elem.get_text(strip=True))
            
        today_views_elem = soup.find("span", attrs={"data-marker": "item-view/today-views"})
        if today_views_elem:
            data["meta"]["today_views"] = clean_text(today_views_elem.get_text(strip=True))

    except Exception as e:
        print(f"Ошибка при парсинге: {e}")

    return data

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Необходимо запустить avito_parser.py")
        return

    input_path = f'{DATA_DIR}/{INPUT_FILE}'
    output_path = f'{DATA_DIR}/{OUTPUT_FILE}'

    if not os.path.exists(input_path):
        print(f"Файл {input_path} не найден.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        items_to_process = json.load(f)

    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            try:
                detailed_results = json.load(f)
                print(f"Загружено {len(detailed_results)}")
            except Exception as e:
                print("Пустой список")
                detailed_results = []
    else:
        detailed_results = []

    processed_urls = {item.get("url") for item in detailed_results if item.get("url")}

    print(f"Всего ссылок в источнике: {len(items_to_process)}")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    
    try:
        for index, item in enumerate(items_to_process):
            url = item.get("url")
            if not url:
                continue

            if url in processed_urls:
                print(f"[{index + 1}/{len(items_to_process)}] Уже собрано: {url}")
                continue

            print(f"[{index + 1}/{len(items_to_process)}] Обрабатываю: {url}")
            
            try:
                driver.get(url)
                
                try: # +captcha чекер
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-marker="item-view/title-info"]'))
                    )
                except:
                    print("Ошибка ожидания")
                    continue

                time.sleep(2)

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                detailed_data = parse_detailed_page(soup, url)
                
                detailed_results.append(detailed_data)
                processed_urls.add(url)

                save_data(detailed_results, output_path)

            except Exception as e:
                print(f"Ошибка в URL {url}: {e}")

            time.sleep(get_random_sleep())

    except Exception as e:
        print(f"Что-то пошло не так: {e}")
    finally:
        driver.quit()
    
    print(f"Всё успешно сохранилось в {output_path}")
    print(f'записей добавилось: {len(detailed_results)}')

if __name__ == "__main__":
    main()