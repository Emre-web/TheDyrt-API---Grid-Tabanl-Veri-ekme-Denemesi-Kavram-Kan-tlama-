

# TheDyrt API - Grid Tabanlı Veri Çekme Denemesi

Bu proje, [TheDyrt](https://thedyrt.com/) API'sini kullanarak belirli bir coğrafi alan içindeki kamp alanlarını grid tabanlı bir yaklaşımla çekmek için yapılan bir denemedir.

## Projenin Amacı

Bu çalışmanın temel amaçları şunlardır:

* **İş Mantığını Anlamak:** Geniş bir coğrafi alanı sistematik olarak küçük hücrelere bölerek ve her bir hücre için API sorguları yaparak veri toplama iş mantığını ve potansiyel zorluklarını anlamak. Özellikle, API'nin belirli bir sorgu başına döndürdüğü lokasyon sayısında bir sınır olduğunda (örneğin, 300-400 lokasyon), bu yoğun hücrelerin nasıl daha küçük alt hücrelere bölünebileceği ve verilerin eksiksiz nasıl toplanabileceği üzerine odaklanmak.
* **Öğrenme Sürecini Göstermek:** Karşılaşılan zorlukları, denenen farklı yaklaşımları ve problem çözme sürecini sergilemek. Bu, özellikle yeni teknolojiler öğrenirken veya karmaşık problemlerle uğraşırken değerli olabilir.
* **Farklı Teknikleri Sergilemek:** Grid tabanlı API sorgulama, yoğun veri yönetimi (hücre bölme) ve API hatalarını ele alma gibi farklı veya ek teknikleri denemek ve sergilemek.
* **Gelecekteki Referans:** İleride benzer bir problemle karşılaşıldığında veya bu koda geri dönülmek istendiğinde bir referans noktası oluşturmak.

## Durum

Bu script, yukarıda belirtilen iş mantığını uygulamak için geliştirilmiş bir **kavram kanıtlama (proof-of-concept) ve deneme çalışmasıdır**. Grid oluşturma, API'ye istek gönderme, gelen yanıtlardaki lokasyon sayısını kontrol etme ve belirli bir eşiği aşan hücreleri alt bölümlere ayırma (subdivision) gibi temel işlevleri içermektedir.

Ancak, bu bir "üretim kalitesinde" veya tamamen tamamlanmış bir çözüm değildir. Geliştirme sürecinde karşılaşılan bazı zorluklar (örneğin, API'nin bazı coğrafi koordinatlar için beklenmedik yanıtlar vermesi, zaman aşımları, hata yönetimi vb.) nedeniyle tam olarak istenen başarıya ulaşılamamış olabilir ve bazı bölümleri iyileştirme veya daha detaylı hata ayıklama gerektirebilir.

Bu kod, benzer bir problemle karşılaşan veya grid tabanlı API veri toplama ve dinamik hücre bölme (dynamic cell subdivision) konseptlerini araştırmak isteyenler için bir başlangıç noktası veya öğrenme materyali olarak değerlendirilebilir.

## Kullanılan Teknolojiler

* Python
* `requests` kütüphanesi (API istekleri için)
* `json` kütüphanesi (JSON verilerini işlemek için)

## Nasıl Çalıştırılır?

1. Gerekli Python kütüphanelerini yükleyin: `pip install requests`
2. Script içindeki coğrafi koordinatları (`LAT_START`, `LAT_END`, `LNG_START`, `LNG_END`) ve adım boyutlarını (`LAT_STEP`, `LNG_STEP`) istediğiniz bölgeye göre ayarlayın.
3. Scripti çalıştırın: `python dryt_scraper.py`

**Not:** API'nin kullanım koşullarına ve hız sınırlamalarına dikkat ediniz. `API_REQUEST_DELAY_SECONDS` gibi değişkenler, API sunucusuna aşırı yüklenmemek için ayarlanmıştır.
