# AI-zen - drrr.com AI Chatbot 🤖

**AI-zen**, [drrr.com](https://drrr.com) anonim chat odalarına bağlanan, **Groq (ücretsiz & hızlı!)** destekli akıllı sohbet botudur. Kullanıcılar `@AI-zen` ile etiketleyerek bot ile konuşabilir.

## ✨ Özellikler

- 🎯 **@AI-zen Etiketleme**: Chat odasında @AI-zen yazarak botu çağırabilirsiniz
- 🧠 **Konuşma Hafızası**: Her kullanıcı için ayrı konuşma geçmişi tutar (max 10 mesaj)
- 🌐 **Çok Dilli**: Türkçe ve İngilizce destekler, mükemmel Türkçe kullanır
- ⚡ **Groq API**: Çok hızlı ve tamamen ücretsiz AI (llama-3.3-70b-versatile)
- 📏 **Kısa Cevaplar**: 140 karakter limitine uygun, öz ve net yanıtlar
- ⏰ **Gerçek Zamanlı**: Her soruda güncel Türkiye saati ve tarih bilgisi
- 🎨 **Modüler Yapı**: Kolay genişletilebilir modül sistemi
- 🔐 **Cloudflare Koruması**: Cloudflare korumalı sitelere bağlanabilir
- 🚫 **DM Yok**: Sadece oda mesajlarına cevap verir (DM'leri görmezden gelir)
- 👋 **Otomatik Selam**: Odaya katılan herkese hoş geldin mesajı gönderir
- 🛡️ **Owner Authentication**: Owner kullanıcısı için şifre doğrulama sistemi
- ⚙️ **Komut Sistemi**: !yardım, !saat, !unutbeni gibi kullanışlı komutlar
- 🚦 **Rate Limiting**: Kullanıcı başına dakikada 5 istek limiti
- 🧹 **Auto-Cleanup**: 1 saat inaktif kullanıcıların geçmişi otomatik temizlenir
- ✅ **Cevap Validasyon**: Her cevap kalite kontrolünden geçer (min 10, max 100 karakter)
- 🔄 **Fallback Sistemi**: Geçersiz cevaplarda otomatik yedek yanıt
- 🚫 **Soru Yasağı**: Bot asla karşı soru sormaz, sadece cevap verir

## 📋 Gereksinimler

- Python 3.12+ (3.8+ de çalışır)
- Groq API Key (Ücretsiz: [console.groq.com](https://console.groq.com))
- drrr.com cookies (drrr-session-1, cf_clearance)

### Gerekli Paketler

```bash
pip install aiohttp aiofiles curl_cffi groq python-dotenv
```

## 🚀 Kurulum

### 1. Projeyi İndirin

```bash
git clone https://github.com/yourusername/AIzen.git
cd AIzen
```

### 2. Bağımlılıkları Yükleyin

```bash
pip install aiohttp aiofiles curl_cffi groq python-dotenv
```

### 3. Groq API Key Alın (Ücretsiz!)

1. [console.groq.com](https://console.groq.com) adresine gidin
2. Ücretsiz hesap oluşturun (Google ile giriş yapabilirsiniz)
3. API Keys bölümünden yeni bir key oluşturun
4. Key'i kopyalayın

### 4. .env Dosyası Oluşturun

Proje klasöründe `.env` dosyası oluşturun ve API key'inizi ekleyin:

```env
GROQ_API_KEY=gsk_your-api-key-here
```

**Not:** `.env` dosyası Git'e eklenmez (güvenlik için)

### 5. Config Dosyasını Düzenleyin

`config.txt` dosyasını açın ve ayarları yapın:

```txt
# Bot kullanıcı adı
name = AI-zen

# Tripcode (opsiyonel, None olarak bırakabilirsiniz)
tc = None

# Avatar ismi (drrr.com'da mevcut avatarlardan seçin)
avatar = setton

# Bağlanmak istediğiniz oda ID'si
# Örnek: https://drrr.com/room/QqzLKhf3ux -> QqzLKhf3ux
roomID = QqzLKhf3ux

# User agent
agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Yüklenecek modüller
mods = AIzen

# Mesaj gönderme gecikme süresi (saniye) - min 1.5 önerilir
throttle = 1.5
```

### 6. Cookies Alımı

Bot çalıştırıldığında sizden iki cookie isteyecek:

1. **drrr-session-1**: drrr.com'a tarayıcınızla girin
2. Browser Developer Tools açın (F12)
3. Application/Storage > Cookies > https://drrr.com
4. `drrr-session-1` ve `cf_clearance` değerlerini kopyalayın

## 🎮 Kullanım

Bot'u başlatın:

```bash
python main.py
```

İlk çalıştırmada cookies girmeniz istenecek:
```
【请输入cookies】
drrr-session-1: [buraya cookie'nizi yapıştırın]
cf_clearance: [buraya cf_clearance'ı yapıştırın]
```

### Chat Odasında Kullanım

**Bot'a Soru Sormak:**
```
@AI-zen merhaba nasılsın?
@AI-zen saat kaç?
@AI-zen bugün hava nasıl?
@AI-zen Python nedir?
```

**Komutlar:**
```
!yardım        - Yardım mesajını gösterir
!saat          - Güncel Türkiye saati ve tarihini gösterir
!unutbeni      - Sizinle olan konuşma geçmişini siler
```

**Owner Komutları (sadece owner):**
```
!stats         - Bot istatistiklerini gösterir
!model [isim]  - AI modelini değiştirir
!temp [0-2]    - Temperature ayarını değiştirir
!clear @user   - Kullanıcının geçmişini temizler
```

**Özellikler:**
- ✅ Kısa ve öz cevaplar verir (max 100 karakter)
- ✅ Güncel tarih ve saat bilgisini bilir
- ✅ Her kullanıcı için konuşma geçmişi tutar
- ✅ Türkçe ve İngilizce anlayıp cevap verir
- ✅ Odaya katılanlara otomatik selam verir
- ✅ "Sen kimsin?" gibi sorulara özel tanıtım yapar
- ❌ DM (özel mesaj) kabul etmez
- 🔒 Owner authentication (aizen kullanıcısı için şifre doğrulama)

### Bot'u Durdurma

Terminal'de `Ctrl+C` ile bot'u güvenli şekilde kapatabilirsiniz.

## 🛠️ Özelleştirme

### AI Model Değiştirme

[modules/AIzen.py](modules/AIzen.py) dosyasında Groq modelini değiştirebilirsiniz:

```python
# Groq'ta mevcut ücretsiz modeller:
self.model = "llama-3.3-70b-versatile"   # Daha güçlü ve doğal (ÖNERİLEN)
self.model = "llama-3.1-8b-instant"      # Hızlı ve hafif
self.model = "mixtral-8x7b-32768"        # Uzun context window
```

**Not:** Bot varsayılan olarak `llama-3.3-70b-versatile` kullanır (daha doğal cevaplar).

### AI Personality Değiştirme

`modules/AIzen.py` içinde system prompt'u düzenleyin:

```python
self.system_prompt = """
Sen AIzen, drrr.com'da samimi bir AI asistanısın.
Kısa ve öz cevaplar ver (max 100 karakter).
Emoji kullanabilirsin 😊
"""
```

### Karakter Limiti Ayarlama

Cevap uzunluğunu `modules/AIzen.py` içinde ayarlayabilirsiniz:

```python
completion = self.client.chat.completions.create(
    model=self.model,
    messages=messages,
    max_tokens=200,       # Buradan ayarlayın
    temperature=0.8,      # 0.0-2.0 arası (düşük = tutarlı, yüksek = yaratıcı)
)
```

### Yeni Modül Ekleme

1. `modules/` klasörüne yeni `.py` dosyası oluşturun:

```python
from modules.module import Module

class MyModule(Module):
    def __init__(self, bot):
        super().__init__(bot)
    
    @property
    def cmds(self):
        return {
            'hello': r'!hello',
            'calc': r'!calc (.+)'
        }
    
    def hello(self, msg):
        self.bot.send(f"Merhaba {msg.user.name}!")
    
    def calc(self, msg):
        # msg.groups[0] ile regex gruplarına erişin
        expression = msg.groups[0]
        # Hesaplama yap...
        self.bot.send(f"Sonuç: {result}")
```

2. `config.txt` içinde modülü aktif edin:
```txt
mods = AIzen,MyModule
```

## 📁 Proje Yapısı

```
AIzen/
├── main.py                 # Ana program
├── networking.py           # drrr.com bağlantı yönetimi
├── config.txt             # Konfigürasyon
├── requirements.txt       # Python bağımlılıkları
├── modules/
│   ├── __init__.py
│   ├── module.py          # Base module sınıfı
│   └── AIzen.py           # AI chatbot modülü
├── popyo/                 # drrr.com API wrapper
│   ├── __init__.py
│   ├── message.py
│   ├── outgoing_message.py
│   ├── room.py
│   ├── user.py
│   └── utils.py
├── logs/                  # Chat logları (otomatik oluşturulur)
└── cookies/               # Cookie dosyaları (otomatik oluşturulur)
```

## 🔧 Sorun Giderme

## 🔧 Sorun Giderme

### "GROQ_API_KEY bulunamadı" Hatası
**Çözüm:** `.env` dosyasının proje klasöründe olduğundan ve doğru formatta olduğundan emin olun:
```env
GROQ_API_KEY=gsk_your-key-here
```

### "Error code: 400 - Model has been decommissioned" Hatası
**Çözüm:** `modules/AIzen.py` içinde model adını güncelleyin:
```python
self.model = "llama-3.3-70b-versatile"  # Güncel önerilen model (70B)
# veya
self.model = "llama-3.1-8b-instant"     # Daha hızlı alternatif (8B)
```

### "Cookie geçersiz" / "认证错误" Hatası
**Çözüm:** 
- Cookies'lerin süresi dolmuş olabilir, tarayıcıdan yeniden alın
- `drrr-session-1` ve `cf_clearance` cookies'lerini kontrol edin
- drrr.com'dan çıkış yapıp tekrar giriş yapın

### Proxy Bağlantı Hatası
**Çözüm:** `networking.py` içinde proxy'yi devre dışı bırakın:
```python
proxies = None  # Proxy kullanmıyorsanız
```

### UnicodeEncodeError (Çince karakter hatası)
**Çözüm:** Bu sorun düzeltildi. Log dosya isimleri artık `YYYY-MM-DD.log` formatında.

### "Module not found: groq" Hatası
**Çözüm:** Groq paketini yükleyin:
```bash
pip install groq
```

### Bot mesaj göndermiyor
**Kontrol edilecekler:**
- `throttle` değeri en az 1.5 saniye olmalı
- Rate limit'e takılmış olabilirsiniz, biraz bekleyin
- Terminal'de hata mesajlarını kontrol edin

### JSON Decode Hatası
**Çözüm:** Bu sorun düzeltildi. Boş response kontrolü eklendi.

## 🤝 Katkıda Bulunma

Bu proje [stozn/drrr-bot](https://github.com/stozn/drrr-bot) temel alınarak geliştirilmiştir.

Katkıda bulunmak isterseniz:
1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## ⚠️ Uyarılar

- Bot'u spam yapmak için kullanmayın
- drrr.com kurallarına uyun
- API rate limitlerini aşmayın
- Throttle değerini en az 1.5 saniye tutun
- Cookies'lerinizi güvende tutun ve paylaşmayın

## 📜 Değişiklik Geçmişi

### v1.0 - Mevcut Versiyon
- ✅ Groq API entegrasyonu (llama-3.3-70b-versatile)
- ✅ @AI-zen etiketleme ile cevap verme
- ✅ Gerçek zamanlı Türkiye saati ve tarih bilgisi
- ✅ Kullanıcı başına konuşma geçmişi (max 10 mesaj)
- ✅ 140 karakter limiti uyumu
- ✅ Mükemmel Türkçe dil desteği
- ✅ DM desteği kaldırıldı (sadece oda mesajları)
- ✅ Proxy sorunu düzeltildi
- ✅ JSON parsing hataları giderildi
- ✅ Log dosya ismi encoding sorunu çözüldü
- ✅ 'knock' mesaj tipi desteği
- ✅ Windows event loop uyumluluğu
- ✅ .env dosyası ile güvenli API key yönetimi

### Planlanmış Özellikler
- 🔄 7/24 cloud deployment (Fly.io/Railway)
- 🔄 Web dashboard (bot istatistikleri)
- 🔄 Çoklu oda desteği
- 🔄 Custom komutlar sistemi
- 🔄 Rate limit otomatik yönetimi

## 🙏 Teşekkürler

- [stozn/drrr-bot](https://github.com/stozn/drrr-bot) - Base bot implementasyonu
- [OpenAI](https://openai.com) - GPT API
- [drrr.com](https://drrr.com) - Chat platformu

## 📧 İletişim

Sorularınız için issue açabilirsiniz.

---

**NGroq](https://groq.com) - Ücretsiz ve hızlı AIrumlu kullanın! 🎓
