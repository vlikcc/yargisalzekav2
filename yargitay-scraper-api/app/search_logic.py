# /yargitay-scraper-api/app/search_logic.py
# KULLANICI GÖRSELİNE GÖRE GÜNCELLENMİŞ VE DOĞRULANMIŞ VERSİYON

import threading
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .schemas import ResultItem
from .config import settings

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def initial_page_load(driver, url: str):
    """Sadece ilk sayfa yüklemesi için kullanılır"""
    logger.info(f"İlk sayfa yükleniyor: {url}")
    driver.get(url)
    WebDriverWait(driver, 20).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def extract_row_data(row) -> dict | None:
    """Bir satır elementinden temel verileri çıkarır."""
    try:
        columns = row.find_elements(By.TAG_NAME, "td")
        if len(columns) >= 5:
            return {
                "daire": columns[1].text.strip(),
                "esas_no": columns[2].text.strip(),
                "karar_no": columns[3].text.strip(),
                "karar_tarihi": columns[4].text.strip()
            }
        return None
    except Exception as e:
        logger.warning(f"Satır verisi çıkarılamadı: {e}")
        return None

def get_decision_text(driver, wait) -> str:
    """
    Sağ panelde görüntülenen karar metnini alır.
    Her tıklamadan sonra bu panelin içeriği güncellenir.
    """
    try:
        # Karar metni alanının yüklenmesini ve görünür olmasını bekle
        decision_element = wait.until(EC.visibility_of_element_located((By.ID, "kararAlani")))
        # İçeriğin tam olarak dolması için küçük bir ek bekleme faydalı olabilir
        time.sleep(0.5) 
        return decision_element.text.strip()
    except TimeoutException:
        logger.warning("Karar metni elementi bulunamadı veya zamanında yüklenmedi.")
        return "Karar metni bulunamadı."
    except Exception as e:
        logger.error(f"Karar metni alınırken beklenmedik bir hata oluştu: {e}")
        return "Karar metni alınamadı."

def wait_for_page_load(driver, wait, page_identifier_element_locator):
    """Sayfa geçişlerinde (örneğin sonraki sayfaya tıklayınca) sayfanın tam olarak yüklenmesini bekler."""
    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        wait.until(EC.presence_of_element_located(page_identifier_element_locator))
        logger.debug("Sayfa başarıyla yüklendi ve doğrulandı.")
        return True
    except TimeoutException:
        logger.warning("Sayfa yüklenirken veya sayfa kimlik öğesi beklenirken zaman aşımına uğradı.")
        return False

def process_page_rows(driver, wait, thread_name, found_count, processed_cases, results, keyword):
    """
    Mevcut sayfadaki satırları tek tek işler.
    Her satıra tıklandığında, karar metni aynı sayfanın sağ panelinde belirir.
    Bu nedenle sayfa yenileme veya geri dönme işlemi GEREKMEZ.
    """
    try:
        # Sayfadaki tüm satırları döngüden önce BİR KEZ alıyoruz.
        # Sayfa değişmediği için Stale Element riski yoktur.
        rows = driver.find_elements(By.CSS_SELECTOR, "#detayAramaSonuclar tbody tr")
        if not rows:
            logger.warning(f"[{thread_name}] Bu sayfada işlenecek satır bulunamadı.")
            return found_count

        logger.info(f"[{thread_name}] Sayfada {len(rows)} adet satır bulundu. İşlem başlıyor...")

        for i, row in enumerate(rows):
            if found_count >= settings.TARGET_RESULTS_PER_KEYWORD:
                logger.info(f"[{thread_name}] Hedeflenen sonuç sayısına ulaşıldı. Bu sayfanın işlenmesi durduruluyor.")
                break

            try:
                # Satırdan temel verileri çıkar
                row_data = extract_row_data(row)
                if not row_data:
                    logger.warning(f"[{thread_name}] Satır {i + 1} için veri çıkarılamadı, atlanıyor.")
                    continue

                case_id = f"{row_data['esas_no']}-{row_data['karar_no']}"
                if case_id in processed_cases:
                    logger.info(f"[{thread_name}] Karar {case_id} daha önce işlenmiş, atlanıyor.")
                    continue
                
                logger.info(f"[{thread_name}] Satır {i + 1}/{len(rows)} işleniyor: {case_id}")

                # Satıra tıkla ve sağdaki panelin güncellenmesini tetikle
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(0.2)
                row.click()

                # Karar metnini al (get_decision_text fonksiyonu panelin yüklenmesini bekleyecektir)
                karar_metni = get_decision_text(driver, wait)
                
                # Sonucu listeye ekle
                result_item = ResultItem(**row_data, karar_metni=karar_metni, keyword=keyword)
                results.append(result_item)
                processed_cases.add(case_id)
                found_count += 1
                logger.success(f"[{thread_name}] Karar {case_id} başarıyla işlendi. Toplam bulunan: {found_count}/{settings.TARGET_RESULTS_PER_KEYWORD}")

            except Exception as e:
                logger.error(f"[{thread_name}] Satır {i + 1} işlenirken bir hata oluştu: {e}")
                # Bu satırda hata olsa bile bir sonraki satıra devam et
                continue

        logger.info(f"[{thread_name}] Sayfa işleme tamamlandı.")
        return found_count

    except Exception as e:
        logger.error(f"[{thread_name}] Sayfa işlenirken genel bir hata oluştu: {e}")
        return found_count

# search_single_keyword fonksiyonu, sayfalama (pagination) mantığı doğru olduğu için
# büyük ölçüde aynı kalabilir. Sadece process_page_rows'u doğru çağırması yeterlidir.

def search_single_keyword(keyword: str, thread_id: int) -> tuple:
    """Tek bir anahtar kelime için Yargıtay sitesinde arama yapar ve sonuçları toplar."""
    driver = None
    thread_name = f"Thread-{thread_id}-{keyword}"
    threading.current_thread().name = thread_name

    try:
        logger.info(f"[{thread_name}] ARAMA BAŞLATILIYOR: '{keyword}'")

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Remote(
            command_executor=settings.SELENIUM_GRID_URL,
            options=chrome_options
        )
        wait = WebDriverWait(driver, 20)

        results = []
        found_count = 0
        processed_cases = set()

        initial_page_load(driver, "https://karararama.yargitay.gov.tr")
        
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "aranan")))
        search_box.clear()
        search_box.send_keys(keyword)
        
        # Ekran görüntüsündeki arama butonu "Ara" yazıyor, ID'si "aramaG" olmayabilir.
        # "Ara" metnini içeren bir butonu bulmak daha sağlam olabilir.
        # XPath //button[normalize-space()='Ara']
        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Ara']")))
        search_button.click()
        
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#detayAramaSonuclar tbody tr")))
            logger.info(f"[{thread_name}] Arama sonuçları başarıyla yüklendi.")
        except TimeoutException:
            logger.warning(f"[{thread_name}] '{keyword}' için herhangi bir sonuç bulunamadı.")
            return (keyword, [], True, "Sonuç bulunamadı")

        page_number = 1
        while found_count < settings.TARGET_RESULTS_PER_KEYWORD and page_number <= settings.MAX_PAGES_TO_SEARCH:
            logger.info(f"[{thread_name}] Sayfa {page_number} işleniyor... (Bulunan: {found_count}/{settings.TARGET_RESULTS_PER_KEYWORD})")

            found_count = process_page_rows(driver, wait, thread_name, found_count, processed_cases, results, keyword)

            if found_count >= settings.TARGET_RESULTS_PER_KEYWORD:
                logger.success(f"[{thread_name}] Hedeflenen sonuç sayısına ({found_count}) ulaşıldı. Arama tamamlandı.")
                break

            try:
                # Sonraki sayfa butonunu bul
                next_button = driver.find_element(By.CSS_SELECTOR, "a.paginate_button.next")
                
                # Buton tıklanabilir değilse (disabled ise), son sayfadayız demektir.
                if "disabled" in next_button.get_attribute("class"):
                    logger.info(f"[{thread_name}] Son sayfaya ulaşıldı. Başka sayfa yok.")
                    break
                
                logger.info(f"[{thread_name}] Sayfa {page_number + 1}'e geçiliyor...")
                driver.execute_script("arguments[0].click();", next_button)
                # Yeni sayfanın tablosunun yüklenmesini bekle
                wait_for_page_load(driver, wait, (By.ID, "detayAramaSonuclar"))
                page_number += 1

            except NoSuchElementException:
                logger.info(f"[{thread_name}] 'Sonraki sayfa' butonu bulunamadı. Muhtemelen tek sayfa sonuç var.")
                break
            except Exception as e:
                logger.error(f"[{thread_name}] Sonraki sayfaya geçerken bir hata oluştu: {e}")
                break

        logger.success(f"[{thread_name}] Arama tamamlandı! Toplam {found_count} sonuç bulundu.")
        return (keyword, results, True, f"{found_count} sonuç bulundu.")

    except Exception as e:
        logger.critical(f"[{thread_name}] Görev sırasında kritik bir hata oluştu: {e}", exc_info=True)
        return (keyword, [], False, str(e))

    finally:
        if driver:
            driver.quit()
            logger.info(f"[{thread_name}] WebDriver kapatıldı.")