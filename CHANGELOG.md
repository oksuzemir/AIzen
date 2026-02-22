# Changelog

Tüm önemli değişiklikler bu dosyada belgelenmektedir.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) standardına uygun

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

### Model Değişiklikleri
1. **İlk**: llama3-8b-8192 (deprecated)
2. **Güncel**: llama-3.1-8b-instant (aktif)

### Mimari Değişiklikler
- **Başlangıç**: Sync HTTP requests
- **v0.5**: Async/await pattern
- **v1.0**: Full async with curl_cffi

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

### Güncel Yapı (v1.0.0)
```
Python: 3.12.2+
aiohttp: 3.10.11
aiofiles: latest
curl_cffi: 0.7.3
groq: 1.0.0
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
- **AI Provider**: [Groq](https://groq.com)

---

## Kaynaklar 📚

- [drrr.com](https://drrr.com) - Hedef platform
- [Groq API Docs](https://console.groq.com/docs)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [curl_cffi](https://github.com/yifeikong/curl_cffi)

---

**Son Güncelleme**: 22 Şubat 2026
