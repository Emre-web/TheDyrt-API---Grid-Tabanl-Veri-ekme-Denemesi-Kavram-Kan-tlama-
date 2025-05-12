"""
TheDyrt API - Grid Tabanlı Veri Çekme Denemesi (Kavram Kanıtlama)

Bu script, TheDyrt API'sini kullanarak belirli bir coğrafi alan içindeki kamp alanlarını
grid tabanlı bir yaklaşımla çekmek için yapılan bir kavram kanıtlama (proof-of-concept)
ve deneme çalışmasıdır.

Temel amaç, geniş bir coğrafi alanı sistematik olarak küçük hücrelere bölerek,
API sorguları yaparak veri toplama iş mantığını ve hücre yoğunluğu durumunda
alt bölümlere ayırma (subdivision) mekanizmasını test etmektir.

Bu bir üretim kalitesinde veya tamamen tamamlanmış bir çözüm değildir.
"""
import requests
import time
import urllib.parse # URL encoding için
import json # JSON işleme için

# Grid Parameters for USA
LAT_START = 24.396308
LAT_END = 49.384358
LNG_START = -125.0
LNG_END = -66.93457
LAT_STEP = 0.1  # API ile daha küçük adımlar
LNG_STEP = 0.1 # API ile daha küçük adımlar

# API Temel Bilgileri
MAX_LOCATIONS_PER_CELL = 350 # Bir hücrede kabul edilebilir maksimum lokasyon sayısı
MAX_SUBDIVISION_DEPTH = 2 # Bir hücrenin maksimum kaç kez alt bölümlere ayrılabileceği
INITIAL_SCRIPT_WAIT_SECONDS = 0 # Saniye cinsinden ilk bekleme süresi (Kullanıcı isteği üzerine kaldırıldı)
MAX_REQUEST_RETRIES = 3
RETRY_REQUEST_DELAY_SECONDS = 5
API_BASE_URL = "https://thedyrt.com/api/v6/locations/search-results"
PAGE_SIZE = 500 # API'den her seferinde kaç sonuç istenecek
API_REQUEST_DELAY_SECONDS = 0.5 # API'ye yüklenmemek için bekleme

def get_data_from_api(bbox_str):
    """
    Belirli bir bbox için API'den tüm sayfalardaki verileri çeker.
    """
    all_data = []
    current_page = 1
    total_pages = 1 # Başlangıçta en az bir sayfa olduğunu varsayalım
    last_url = None

    # Sabit filtre parametreleri
    base_params = {
        "filter[search][drive_time]": "any",
        "filter[search][air_quality]": "any",
        "filter[search][electric_amperage]": "any",
        "filter[search][max_vehicle_length]": "any",
        "filter[search][price]": "any",
        "filter[search][rating]": "any",
        "filter[search][bbox]": bbox_str,
        "sort": "recommended",
        "page[size]": PAGE_SIZE  # PAGE_SIZE global olarak 500 tanımlı olmalı
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    while current_page <= total_pages:
        retries = 0
        request_successful = False
        
        while retries < MAX_REQUEST_RETRIES and not request_successful:
            params = base_params.copy()
            params["page[number]"] = current_page
            
            try:
                response = requests.get(API_BASE_URL, params=params, headers=headers, timeout=30)
                last_url = response.url
                response.raise_for_status()
                data = response.json()

                if current_page == 1:
                    meta = data.get('meta', {})
                    retrieved_page_count = meta.get('page-count')
                    if retrieved_page_count is not None and isinstance(retrieved_page_count, int) and retrieved_page_count > 0:
                        total_pages = retrieved_page_count
                        print(f"{bbox_str} için toplam {total_pages} sayfa bulundu.")
                    else:
                        print(f"Uyarı: {bbox_str} için 'page-count' meta bilgisi alınamadı veya geçersiz. Yalnızca ilk sayfa işlenecek.")
                        total_pages = 1 

                page_data = data.get('data', [])
                if page_data:
                    all_data.extend(page_data)
                    print(f"Sayfa {current_page}/{total_pages} ({bbox_str}) alındı, {len(page_data)} lokasyon eklendi. Toplam: {len(all_data)}")
                else:
                    print(f"Sayfa {current_page}/{total_pages} ({bbox_str}) veri içermiyor veya 'data' anahtarı yok.")
                    if current_page == 1 and total_pages == 1: 
                        break # No data even on the first page, and no other pages to check

                request_successful = True # Mark as successful to exit retry loop

            except requests.exceptions.HTTPError as http_err:
                retries += 1
                print(f"{bbox_str} için HTTP hatası (sayfa {current_page}, deneme {retries}/{MAX_REQUEST_RETRIES}): {http_err} - Durum: {response.status_code if 'response' in locals() else 'N/A'}")
                if retries >= MAX_REQUEST_RETRIES:
                    print(f"{bbox_str} için maksimum HTTP deneme sayısına ulaşıldı. Bu bbox için sayfa {current_page} atlanıyor.")
                    # Bu durumda döngüden çıkıp bir sonraki sayfaya (eğer varsa) veya bbox'a geçmeyi düşünebiliriz.
                    # Şimdilik, bu sayfa için işlemi bitirip, toplanan veriyle dönüyoruz.
                    return {"data": all_data, "meta": {}, "links": {}}, last_url
                print(f"{RETRY_REQUEST_DELAY_SECONDS} saniye sonra yeniden denenecek...")
                time.sleep(RETRY_REQUEST_DELAY_SECONDS)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_timeout_err:
                retries += 1
                print(f"{bbox_str} için bağlantı/zaman aşımı (sayfa {current_page}, deneme {retries}/{MAX_REQUEST_RETRIES}): {conn_timeout_err}")
                if retries >= MAX_REQUEST_RETRIES:
                    print(f"{bbox_str} için maksimum bağlantı/zaman aşımı deneme sayısına ulaşıldı. Bu bbox atlanıyor.")
                    return {"data": all_data, "meta": {}, "links": {}}, last_url # Bu bbox için işlemi sonlandır
                print(f"{RETRY_REQUEST_DELAY_SECONDS} saniye sonra yeniden denenecek...")
                time.sleep(RETRY_REQUEST_DELAY_SECONDS)
            except requests.exceptions.RequestException as req_err:
                # Diğer beklenmedik request hataları için
                print(f"{bbox_str} için genel istek hatası (sayfa {current_page}): {req_err}")
                # Bu tür hatalar genellikle yeniden denemeyle çözülmez, bu yüzden bu bbox için işlemi durduralım.
                return {"data": all_data, "meta": {}, "links": {}}, last_url
            except json.JSONDecodeError:
                response_text_snippet = response.text[:200] if 'response' in locals() and hasattr(response, 'text') else "Yanıt metni yok"
                print(f"{bbox_str} için JSON çözümleme hatası (sayfa {current_page}). Yanıt: {response_text_snippet}...")
                # JSON hatası genellikle yeniden denemeyle çözülmez.
                return {"data": all_data, "meta": {}, "links": {}}, last_url
        
        if not request_successful:
            # Eğer MAX_RETRIES sonrasında bile başarılı bir istek yapılamadıysa, bu bbox için işlemi sonlandır.
            print(f"{bbox_str} için tüm denemeler (sayfa {current_page}) başarısız oldu. Bu bbox atlanıyor.")
            # Fonksiyonun geri kalanı zaten mevcut veriyi döndürecektir.
            # Ancak, belirli bir sayfada takılıp kalmamak için burada çıkmak daha iyi olabilir.
            return {"data": all_data, "meta": {}, "links": {}}, last_url

        current_page += 1
        if current_page <= total_pages:
            print(f"{bbox_str} için bir sonraki sayfaya geçiliyor: {current_page}. {API_REQUEST_DELAY_SECONDS} saniye bekleniyor...")
            time.sleep(API_REQUEST_DELAY_SECONDS)


    if not all_data:
        print(f"{bbox_str} için hiçbir veri toplanamadı.")
        # Belki de last_url'i burada loglamak veya döndürmek isteyebilirsiniz.
        # return {"data": [], "meta": {}, "links": {}}, last_url # Veri yoksa boş bir yapı döndür

    # API'nin döndürdüğü tam yapıya benzer bir çıktı oluşturalım
    # Bu, ana kodun veri yapısını bekleme şekliyle uyumlu olmalıdır.
    # Şimdilik, tüm verileri 'data' anahtarı altında birleştirilmiş bir liste olarak döndürüyoruz.
    # 'meta' ve 'links' bilgileri tüm sayfalardan toplanamadığı için, bu örnekte sadece veriyi döndürüyoruz.
    # Eğer ana kod bu meta/links bilgilerini bekliyorsa, bu kısmın güncellenmesi gerekir.
    return {"data": all_data, "meta": {}, "links": {}}, last_url

def process_dense_cell(lat_max_orig, lat_min_orig, lng_min_orig, lng_max_orig, current_depth):
    """
    Yoğun bir ızgara hücresini işler. Lokasyon sayısı MAX_LOCATIONS_PER_CELL'i aşarsa,
    hücreyi 4 alt hücreye böler ve bu fonksiyonu her bir alt hücre için özyinelemeli olarak çağırır.
    Maksimum MAX_SUBDIVISION_DEPTH derinliğine kadar alt bölümlere ayırır.
    """
    indent_space = '  ' * current_depth
    indent_space_sub = '  ' * (current_depth + 1)

    print(f"{indent_space}Yoğun hücre işleniyor (Derinlik: {current_depth}): LAT {lat_max_orig:.5f}-{lat_min_orig:.5f}, LNG {lng_min_orig:.5f}-{lng_max_orig:.5f}")

    if current_depth >= MAX_SUBDIVISION_DEPTH: # >= MAX_SUBDIVISION_DEPTH daha doğru, çünkü current_depth 0'dan başlarsa ve MAX_SUBDIVISION_DEPTH 2 ise, 0, 1, 2 derinliklerine izin verilir.
        print(f"{indent_space}Maksimum alt bölme derinliğine ({MAX_SUBDIVISION_DEPTH}) ulaşıldı. Bu hücre ({lat_max_orig:.5f}-{lat_min_orig:.5f}, {lng_min_orig:.5f}-{lng_max_orig:.5f}) daha fazla bölünmeyecek.")
        # API'den veriyi normal şekilde çekelim ve kullanıcıya sunalım, lokasyon sayısı ne olursa olsun.
        bbox_str_final_sub = f"{lng_min_orig},{lat_min_orig},{lng_max_orig},{lat_max_orig}"
        api_data_final_sub, requested_url_final_sub = get_data_from_api(bbox_str_final_sub)
        print(f"{indent_space}--- Son kullanılan API URL'i (Maks Derinlik): {requested_url_final_sub} ---")
        if api_data_final_sub and 'data' in api_data_final_sub and isinstance(api_data_final_sub['data'], list):
            locations_in_final_sub_cell = len(api_data_final_sub['data'])
            print(f"{indent_space}{locations_in_final_sub_cell} lokasyon bulundu (Maksimum Derinlik).")
            if locations_in_final_sub_cell > 0:
                print(f"{indent_space}--- Bu son alt hücre için tam API Yanıtı ({locations_in_final_sub_cell} lokasyon): ---")
                print(json.dumps(api_data_final_sub, indent=2, ensure_ascii=False))
            # else: # Zaten 0 lokasyon bulundu mesajı yukarıda var.
        else:
            print(f"{indent_space}--- Bu son alt hücre için API'den veri alınamadı/işlenemedi. ---")
        input(f"{indent_space}DURAKLATILDI (Maks Derinlik). Devam etmek için Enter'a basın...")
        time.sleep(API_REQUEST_DELAY_SECONDS)
        return # Bu hücre için işlem tamamlandı.

    # İlk olarak mevcut hücre için veri çekmeyi deneyelim (main'den gelen orijinal büyük hücre için)
    # Bu adım atlanabilir eğer direkt bölerek başlamak isteniyorsa, ancak ilk sorguyu yapmak tutarlı olabilir.
    # bbox_str_orig = f"{lng_min_orig},{lat_min_orig},{lng_max_orig},{lat_max_orig}"
    # api_data_orig, requested_url_orig = get_data_from_api(bbox_str_orig)
    # locations_in_orig_cell = 0
    # if api_data_orig and 'data' in api_data_orig and isinstance(api_data_orig['data'], list):
    #     locations_in_orig_cell = len(api_data_orig['data'])
    # print(f"{indent_space}Orijinal yoğun hücrede {locations_in_orig_cell} lokasyon bulundu.")

    # if locations_in_orig_cell <= MAX_LOCATIONS_PER_CELL and current_depth == 0: # Eğer ana hücre zaten eşiğin altındaysa (ve bu ilk çağrıysa)
    #     print(f"{indent_space}Orijinal hücredeki lokasyon sayısı ({locations_in_orig_cell}) eşiğin ({MAX_LOCATIONS_PER_CELL}) altında. Bölmeye gerek yok.")
    #     if locations_in_orig_cell > 0:
    #         print(f"{indent_space}--- Orijinal hücre için tam API Yanıtı: ---")
    #         print(json.dumps(api_data_orig, indent=2, ensure_ascii=False))
    #     input(f"{indent_space}DURAKLATILDI (Orijinal Hücre). Devam etmek için Enter'a basın...")
    #     time.sleep(API_REQUEST_DELAY_SECONDS)
    #     return # Bölmeye gerek yok
    
    # Hücreyi 4 alt hücreye böl (2x2 grid)
    lat_mid = (lat_max_orig + lat_min_orig) / 2
    lng_mid = (lng_max_orig + lng_min_orig) / 2

    sub_cells_coords = [
        (lat_max_orig, lat_mid, lng_min_orig, lng_mid),  # Sol üst (Kuzey-Batı)
        (lat_max_orig, lat_mid, lng_mid, lng_max_orig),   # Sağ üst (Kuzey-Doğu)
        (lat_mid, lat_min_orig, lng_min_orig, lng_mid),  # Sol alt (Güney-Batı)
        (lat_mid, lat_min_orig, lng_mid, lng_max_orig)   # Sağ alt (Güney-Doğu)
    ]
    sub_cell_names = ["Sol Üst", "Sağ Üst", "Sol Alt", "Sağ Alt"]

    for i, (s_lat_max, s_lat_min, s_lng_min, s_lng_max) in enumerate(sub_cells_coords):
        print(f"{indent_space_sub}Alt hücre ({sub_cell_names[i]}) işleniyor: LAT {s_lat_max:.5f}-{s_lat_min:.5f}, LNG {s_lng_min:.5f}-{s_lng_max:.5f}")
        bbox_str_sub = f"{s_lng_min},{s_lat_min},{s_lng_max},{s_lat_max}"
        api_data_sub, requested_url_sub = get_data_from_api(bbox_str_sub)
        
        print(f"{indent_space_sub}--- Son kullanılan API URL'i: {requested_url_sub} ---")

        if api_data_sub and 'data' in api_data_sub and isinstance(api_data_sub['data'], list):
            locations_in_sub_cell = len(api_data_sub['data'])
            print(f"{indent_space_sub}{locations_in_sub_cell} lokasyon bulundu.")

            if locations_in_sub_cell > MAX_LOCATIONS_PER_CELL:
                print(f"{indent_space_sub}Bu alt hücrede hala çok fazla lokasyon var ({locations_in_sub_cell} > {MAX_LOCATIONS_PER_CELL}). Tekrar bölünüyor (Derinlik: {current_depth + 1})...")
                process_dense_cell(s_lat_max, s_lat_min, s_lng_min, s_lng_max, current_depth + 1)
            elif locations_in_sub_cell > 0:
                print(f"{indent_space_sub}--- Bu alt hücre için tam API Yanıtı ({locations_in_sub_cell} lokasyon): ---")
                print(json.dumps(api_data_sub, indent=2, ensure_ascii=False))
                input(f"{indent_space_sub}DURAKLATILDI ({sub_cell_names[i]}). Devam etmek için Enter'a basın...")
            else:
                print(f"{indent_space_sub}--- Bu alt hücre için API yanıtında lokasyon bulunamadı. ---")
                input(f"{indent_space_sub}DURAKLATILDI ({sub_cell_names[i]} - Veri Yok). Devam etmek için Enter'a basın...")
        else:
            print(f"{indent_space_sub}--- Bu alt hücre için API'den veri alınamadı/işlenemedi. ---")
            input(f"{indent_space_sub}DURAKLATILDI ({sub_cell_names[i]} - Hata/Veri Yok). Devam etmek için Enter'a basın...")
        
        time.sleep(API_REQUEST_DELAY_SECONDS) # Her alt hücre sorgusu sonrası bekleme


def main():
    print("Script başlıyor...")
    print("--- API Tabanlı Izgara Taraması Başlıyor (Kuzey-Batı'dan Güney-Doğu'ya) ---")
    current_lat = LAT_END  # Kuzeyden başla
    cell_count = 0
    total_locations_found = 0
    all_scraped_data = []

    try:
        while current_lat > LAT_START:
            current_lng = LNG_START
            while current_lng < LNG_END:
                cell_count += 1
                
                lat_max = current_lat
                lat_min = max(current_lat - LAT_STEP, LAT_START) # Enlem adımının başlangıç sınırını aşmamasını sağla
                lng_min = current_lng
                lng_max = min(current_lng + LNG_STEP, LNG_END)   # Boylam adımının bitiş sınırını aşmamasını sağla

                # Geçerli bir hücre olup olmadığını kontrol et (özellikle son adımlarda önemlidir)
                if lat_min >= lat_max or lng_min >= lng_max:
                    current_lng += LNG_STEP # Bir sonraki boylama geç
                    continue

                print(f"Izgara hücresi işleniyor {cell_count}: LAT {lat_max:.5f} (N) - {lat_min:.5f} (S), LNG {lng_min:.5f} (W) - {lng_max:.5f} (E)")

                bbox_str_api = f"{lng_min},{lat_min},{lng_max},{lat_max}"
                api_data, requested_url = get_data_from_api(bbox_str_api)
                print(f"--- Son kullanılan API URL'i: {requested_url} ---")

                if api_data and 'data' in api_data and isinstance(api_data['data'], list):
                    locations_in_cell = len(api_data['data'])
                    print(f"{locations_in_cell} lokasyon bulundu.")

                    if locations_in_cell > MAX_LOCATIONS_PER_CELL:
                        print(f"Bu hücrede çok fazla lokasyon var ({locations_in_cell} > {MAX_LOCATIONS_PER_CELL}). Hücre bölünecek...")
                        process_dense_cell(lat_max, lat_min, lng_min, lng_max, 0)
                    elif locations_in_cell > 0:
                        print("--- Bu hücre için tam API Yanıtı: ---")
                        print(json.dumps(api_data, indent=2, ensure_ascii=False))
                        print("---------------------------------------------------------")
                        total_locations_found += locations_in_cell
                        all_scraped_data.extend(api_data['data'])
                        user_input = input(f"Izgara hücresi {cell_count} tamamlandı. Devam etmek için Enter'a basın (çıkmak için 'q'): ").lower()
                        if user_input in ['q', 'exit']:
                            raise SystemExit("Kullanıcı tarafından çıkış yapıldı.")
                    else:
                        print("--- API yanıtında bu hücre için lokasyon bulunamadı. ---")
                        # Veri olmayan hücreler için input isteğe bağlı, şimdilik yok.
                else:
                    print("--- API'den veri alınamadı veya işlenemedi. Yanıt: ---")
                    print(api_data)
                    user_input = input(f"Izgara hücresi {cell_count} (API hatası). Devam etmek için Enter'a basın (çıkmak için 'q'): ").lower()
                    if user_input in ['q', 'exit']:
                        raise SystemExit("Kullanıcı tarafından çıkış yapıldı.")
                
                # process_dense_cell çağrılmadıysa API gecikmesini uygula
                if not (api_data and 'data' in api_data and isinstance(api_data['data'], list) and len(api_data['data']) > MAX_LOCATIONS_PER_CELL):
                    time.sleep(API_REQUEST_DELAY_SECONDS)

                current_lng += LNG_STEP
            
            current_lat -= LAT_STEP
            if current_lat <= LAT_START and current_lng >= LNG_END : # Eğer son enlem işlendiyse ve tüm boylamlar bittiyse döngüden çık
                 # Bu ek kontrol, son enlem şeridinin tam olarak işlenmesini ve LAT_START'ın altına düşmeden önce döngünün sonlanmasını sağlar.
                 # Eğer current_lat tam LAT_START'a eşitse ve bir sonraki adımda altına düşecekse ve tüm boylamlar işlendiyse, çıkabiliriz.
                 # Veya current_lat < LAT_START ise kesin çık.
                 # Daha basit hali: current_lat <= LAT_START olduğunda dış döngü zaten duracak.
                 pass # Dış döngü koşulu (current_lat > LAT_START) bunu zaten halleder.

        print("--- Tüm ızgara hücreleri işlendi ---")

    except SystemExit as e:
        print(f"Program sonlandırıldı: {e}")
    except Exception as e:
        print(f"Ana işlem sırasında genel bir hata oluştu: {e}")
    finally:
        print("\n--- Tarama Sonuçları ---")
        print(f"Toplam {cell_count} ızgara hücresi işlendi.")
        print(f"Toplam {total_locations_found} lokasyon (potansiyel olarak tekrar edenlerle birlikte) bulundu.")
        # print("Toplanan veriler:")
        # for item in all_scraped_data:
        #     print(item) # Veya daha düzenli bir formatta yazdırılabilir

if __name__ == "__main__":
    main()
    print("\nScript başarıyla sonlandı.")
