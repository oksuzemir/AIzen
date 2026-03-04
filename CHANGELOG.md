# Changelog

Tüm önemli değişiklikler bu dosyada belgelenmektedir.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) standardına uygun

## [1.3.0] - 2026-03-04

### Eklenen ✨
- **Google Gemini 2.5 Flash (Birincil AI)**: Groq yerine Google Gemini thinking model birincil AI olarak eklendi
- **Çoklu API Key Rotasyonu**: 10'a kadar Gemini API key desteği (GEMINI_API_KEY, _2, ..._10)
  - Round-robin + rate-limit-aware rotasyon
  - Key başına 8 RPM güvenlik marjı (free tier 10 RPM)
  - Tüm key'ler tükenince Groq fallback'e geçiş
- **Groq Yedek Sistemi**: Gemini başarısız olursa otomatik Groq fallback
  - Model: deepseek-r1-distill-llama-70b-specdec (llama-3.3-70b'den upgrade)
- **Paralel Mesaj İşleme**: asyncio.create_task() ile eş zamanlı kullanıcı yanıtları
  - ThreadPoolExecutor(max_workers=8) ile blocking operasyonlar
  - Birden fazla kullanıcı aynı anda cevap alabilir
- **Oda Sohbet Farkındalığı**: room_history ile kullanıcılar arası bağlam
  - Son 30 mesaj takibi (tüm kullanıcılardan)
  - [ODA SOHBETİ] context olarak AI'a enjekte edilir
- **Gönderici Tanıma**: `[Yazan: @username]` prefix ile AI kimin yazdığını bilir
- **Çift @username Önleme**: AI cevabından @username strip edilir (kod da ekliyordu)
- **Aile Sistemi**: father=aizen ("baba" hitap), sister=Days ("abla" hitap)
- **DİL KURALI**: Türkçe-only kural, İngilizce yazılsa bile Türkçe cevap
- **120 Karakter Hedef**: Platform limiti 140, bot 120 hedefler (@username için alan)
- **Gelişmiş Konuşma Geçmişi**: 
  - max_history 10→25 mesaj çifti (50 entry)
  - Özel komut yanıtları da geçmişe kaydedilir (film, döviz, hava durumu vb.)
- **Film Arama Genişletme**: istatistik, puan, imdb, rating, oy, gişe, hasılat, oyuncu, yönetmen, bütçe, fragman
- **google-genai Paketi**: requirements.txt'e eklendi

### Değiştirilen 🔄
- **Birincil AI**: Groq → Google Gemini 2.5 Flash (thinking model)
- **Yedek AI Model**: llama-3.3-70b-versatile → deepseek-r1-distill-llama-70b-specdec
- **Kişilik**: Samimi/doğal → Edgy, piç ama sevimli, küfürlü sokak dili
- **Temperature**: 0.7 → 0.8
- **Max Output Tokens**: 150 → 1024 (thinking_budget=256)
- **ThinkingConfig**: thinking_budget=256, Gemini düşünme modeli için token ayrımı
- **Rate Limiting**: 5 → 10 istek/dakika/kullanıcı
- **Karakter Limiti**: 100 → 120 karakter hedef
- **"Sen kimsin" Regex**: `\bsen\s+ne(sin)?\b` → `\bsen\s+nesin\b` (false positive düzeltme)
- **Handler**: `await` → `asyncio.create_task()` (paralel işleme)
- **System Prompt**: Tamamen yeniden yazıldı (edgy kişilik, aile sistemi, oda bağlamı)

### Düzeltilen 🐛
- **Truncated Responses (FinishReason.MAX_TOKENS)**: Gemini thinking model token'ları düşünme+yanıt olarak paylaşıyordu, max_tokens artırıldı
- **Çift @username**: AI cevabında @name + kodun da @name eklemesi → regex strip
- **Dil Karışması**: AI bazen cümle ortasında İngilizce/Çince yazıyordu → DİL KURALI
- **"Ne sence" False Positive**: "sen kimsin" regex'i "ne sence" yakalıyordu → regex daraltıldı
- **Concurrent Message Drop**: `await` engellemesi paralel mesajları engelliyordu → create_task
- **Syntax Error**: Duplicate `] + api_history` satırı kaldırıldı

### Kaldırılan ❌
- **Anne (Mother)**: Aile sözlüğünden ve tüm ilgili koddan kaldırıldı
- **Groq Birincil**: Artık yedek olarak kullanılıyor (Gemini birincil)

## [1.2.0] - 2026-02-22

### Eklenen ✨
- **Cevap Validasyon Sistemi**: AI'ın tüm cevapları validate ediliyor
  - Çok kısa (<10 karakter) cevaplar reject
  - Çok uzun (>100 karakter) cevaplar reject (chunking önlenir)
  - Soru içeren cevaplar reject (? veya soru kelimeleri)
  - Yasaklı kelime/cümle kontrolü
- **Fallback Cevap Sistemi**: Geçersiz cevaplarda otomatik fallback (8 varyant)
- **Soru Kelime Tespiti**: "?" olmadan da soruları yakalar (ne yap, nasıl, neden, vs.)
- **Gelişmiş Debug Logları**: 
  - AI cevabı gösterimi
  - Validasyon hataları gösterimi
  - Fallback kullanımı bildirimi

### Değiştirilen 🔄
- **System Prompt Tamamen Yenilendi**: 
  - 6 madde halinde net kurallar
  - 7 kategori örnek cevaplar
  - Yanlış örnek listesi eklendi
  - Daha anlaşılır ve yapılandırılmış
- **Temperature**: 0.9 → 0.8 → 0.7 (tutarlılık için optimize edildi)
- **Max Tokens**: 200 → 150 (optimal performans)
- **Yasaklı Kelime Listesi**: Genişletildi
  - "ne yaparız", "kahve", "çay", "yemek yedin" eklendi
  - Tüm "günler" kalıpları yasaklandı

### Düzeltilen 🐛
- **"in!" Sorunu**: Tek kelimelik garip cevaplar artık reject ediliyor
- **"ne yaparız lan" Sorunu**: Soru işareti olmayan sorular yakalanıyor
- **"sabahı iyi olsun" Sorunu**: Yasaklı kelime kontrolü ile engellendi
- **Chunking Sorunu**: Uzun cevaplar (>100 char) reject, fallback kullanılıyor

### Güvenilirlik 🛡️
- Minimum 10 karakter garanti
- Maksimum 100 karakter garanti (140 char limitine uyum)
- Soru sorma garanti yok
- Yasaklı kelime kullanımı garanti yok
- Fallback sistemi ile %100 cevap garantisi

## [1.1.0] - 2026-02-22

### Eklenen ✨
- **Bot Adı Değişikliği**: AIzen → AI-zen (tire ile)
- **Model Upgrade**: llama-3.1-8b-instant → llama-3.3-70b-versatile (daha güçlü ve doğal cevaplar)
- **Otomatik Selam**: Odaya katılan her kullanıcıya otomatik "Hoş geldin! 👋😊" mesajı
- **"Sen Kimsin" Özel Cevap**: "Sen kimsin?" gibi sorulara teknoloji detayı olmadan özel tanıtım
- **Owner Authentication**: aizen kullanıcısı için şifre doğrulama sistemi (OWNER_PASSWORD)
- **Komut Sistemi**: !yardım, !saat, !unutbeni komutları eklendi
- **Owner Komutları**: !stats, !model, !temp, !clear (sadece owner kullanabilir)
- **Rate Limiting**: Kullanıcı başına dakikada 5 istek limiti
- **İstatistik Takibi**: Toplam mesaj, benzersiz kullanıcı, uptime takibi
- **Auto-Cleanup**: 1 saat inaktif kullanıcıların geçmişi otomatik temizlenir
- **Sonsuz Döngü Önlemi**: Bot kendi mesajlarına cevap vermeyi önleyen kontrol
- **Personality İyileştirme**: Daha doğal, basit ve arkadaş canlısı system prompt

### Değiştirilen 🔄
- **Temperature**: 0.8 → 0.9 (daha yaratıcı cevaplar)
- **System Prompt**: Tamamen yeniden yazıldı - daha doğal, basit, kasımsız
- **Komut Örnekleri**: Prompt'a "naber" → "iyidir senden naber" gibi örnekler eklendi
- **Owner Kontrolü**: "aizen" kullanıcısı için şifre doğrulama (tire olmadan)

### Düzeltilen 🐛
- **!unutbeni Kontrolü**: Boş liste kontrolü eklendi, sadece gerçek geçmişi siler
- **Kendi Mesajlarına Cevap**: Bot artık kendi gönderdiği mesajlara cevap vermiyor
- **Garip Cevaplar**: "sabahları iyiyim", "güzel günler" gibi garip ifadeler yasaklandı

### Kaldırılan ❌
- **!fal Komutu**: Kahve falı özelliği kaldırıldı
- **Teknoloji Detayları**: "Sen kimsin" cevabından "Groq'un llama modelini kullanıyorum" kaldırıldı

## [1.0.0] - 2026-02-22

### Eklenen ✨
- **Groq AI Entegrasyonu**: Ücretsiz llama-3.1-8b-instant modeli ile AI chatbot
- **@AIzen Etiketleme**: Kullanıcılar @AIzen ile botu çağırabilir
- **Gerçek Zamanlı Context**: Her soruda güncel Türkiye saati ve tarih bilgisi
- **Konuşma Geçmişi**: Her kullanıcı için ayrı conversation history (max 10 mesaj)
- **Çoklu Dil Desteği**: Türkçe ve İngilizce anlama ve yanıt verme
- **Modüler Sistem**: Plugin tabanlı modül yükleme sistemi
- **.env Desteği**: python-dotenv ile güvenli API key yönetimi
- **140 Karakter Limiti**: drrr.com limitine uyumlu kısa cevaplar
- **Mükemmel Türkçe**: AI'a doğal Türkçe kullanması için özel talimat
- **Cloudflare Bypass**: curl_cffi ile Cloudflare korumalı sitelere erişim

### Değiştirilen 🔄
- **OpenAI → Groq**: Ücretsiz olması için API değiştirildi
- **Model Güncelleme**: llama3-8b-8192 → llama-3.1-8b-instant (deprecated model sorunu)
- **Log Formatı**: Çince karakterler → YYYY-MM-DD.log (Unicode hatasını önler)
- **Proxy Ayarı**: Varsayılan olarak kapalı (proxies = None)
- **DM Davranışı**: Artık özel mesajlara cevap vermiyor (sadece oda mesajları)

### Düzeltilen 🐛
- **Proxy Hatası**: 127.0.0.1:7890 proxy bağlantı hatası (proxy devre dışı bırakıldı)
- **JSON Parsing**: Boş veya hatalı response kontrolü eklendi
- **Encoding Error**: Log dosya isimlerinde Çince karakter hatası
- **None User**: User object None kontrolü eklendi (AttributeError önlendi)
- **Module Import**: AIzen modülü groq paketi ile doğru import ediliyor
- **API Key Loading**: .env dosyası load_dotenv() ile doğru zamanda yükleniyor
- **Event Loop**: Windows için WindowsSelectorEventLoopPolicy eklendi
- **Knock Message**: 'knock' mesaj tipi desteği eklendi

### Kaldırılan ❌
- **DM Desteği**: Bot artık özel mesajlara cevap vermiyor
- **Whisper Feature**: Denendi ve kaldırıldı (normal mesaj gönderimi korundu)
- **OpenAI Dependency**: Groq'a geçiş ile OpenAI bağımlılığı kaldırıldı

### Güvenlik 🔒
- API anahtarları .env dosyasında saklanıyor
- .gitignore ile hassas dosyalar Git'e eklenmiyor
- Cookie bilgileri runtime'da alınıyor (kodda saklanmıyor)

## [0.1.0] - Başlangıç

### Eklenen
- stozn/drrr-bot projesi temel alındı
- Temel drrr.com bağlantı sistemi
- Modül yükleme sistemi
- Mesaj polling loop
- Cookie authentication

---

## Planlanan Özellikler 🚀

### [1.1.0] - Gelecek Versiyon
- [ ] 7/24 Cloud deployment (Fly.io/Railway)
- [ ] Web dashboard (bot istatistikleri)
- [ ] Çoklu oda desteği
- [ ] Custom komutlar sistemi
- [ ] Rate limit otomatik yönetimi
- [ ] Mesaj analitikleri
- [ ] Kullanıcı reputasyon sistemi

### [1.2.0] - İleriki Planlar
- [ ] Voice mesaj desteği (eğer drrr.com desteklerse)
- [ ] Image/URL analizi
- [ ] Scheduled messages
- [ ] Auto-moderation
- [ ] Multi-language responses (İngilizce/Türkçe otomatik algılama)

---

## Teknolojik Değişim Geçmişi

### AI Provider Değişiklikleri
1. **v0.1**: OpenAI GPT-3.5/GPT-4 (ücretli)
2. **v1.0**: Groq llama-3.1-8b-instant (ücretsiz)
3. **v1.3**: Google Gemini 2.5 Flash (birincil, ücretsiz) + Groq deepseek-r1 (yedek)

### Model Değişiklikleri
1. **İlk**: llama3-8b-8192 (deprecated)
2. **v1.1**: llama-3.3-70b-versatile (aktif)
3. **v1.3**: gemini-2.5-flash (birincil) + deepseek-r1-distill-llama-70b-specdec (yedek)

### Mimari Değişiklikler
- **Başlangıç**: Sync HTTP requests
- **v0.5**: Async/await pattern
- **v1.0**: Full async with curl_cffi
- **v1.3**: Parallel processing (asyncio.create_task), multi-key rotation, dual context system

---

## Bilinen Sorunlar 🐛

### Kritik
Yok

### Orta Seviye
- Rate limiting elle yönetiliyor (otomatik değil)
- Tek oda desteği (multi-room yok)

### Düşük Seviye
- Log dosyaları temizlenmiyor (manuel silme gerekli)
- Conversation history RAM'de tutuluyor (veritabanı yok)

---

## Bağımlılık Versiyonları

### Güncel Yapı (v1.3.0)
```
Python: 3.12.2+
aiohttp: 3.10.11
aiofiles: latest
curl_cffi: 0.7.3
groq: 1.0.0
google-genai: latest
python-dotenv: latest
```

### Önemli Notlar
- Python 3.8+ minimum gereksinim
- Windows için WindowsSelectorEventLoopPolicy gerekli
- curl_cffi Cloudflare bypass için kritik

---

## Katkıda Bulunanlar 👥

- **Ana Geliştirici**: AIzen Projesi
- **Temel Framework**: [stozn/drrr-bot](https://github.com/stozn/drrr-bot)
- **AI Provider**: [Google Gemini](https://aistudio.google.com) (birincil) / [Groq](https://groq.com) (yedek)

---

## Kaynaklar 📚

- [drrr.com](https://drrr.com) - Hedef platform
- [Groq API Docs](https://console.groq.com/docs)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [curl_cffi](https://github.com/yifeikong/curl_cffi)

---

**Son Güncelleme**: 4 Mart 2026
