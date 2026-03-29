# AI-zen - drrr.com AI Chatbot 🤖

**AI-zen**, [drrr.com](https://drrr.com) anonim chat odalarına bağlanan, **Groq (llama-3.3-70b-versatile, ücretsiz)** destekli akıllı sohbet botudur. Kullanıcılar `@AI-zen` ile etiketleyerek bot ile konuşabilir.

## ✨ Özellikler

- 🎯 **@AI-zen Etiketleme**: Chat odasında @AI-zen yazarak botu çağırabilirsiniz
- 🧠 **Konuşma Hafızası**: Her kullanıcı için ayrı konuşma geçmişi tutar (max 15 mesaj çifti)
- 🏠 **Oda Sohbet Farkındalığı**: Son 20 mesajı takip ederek kullanıcılar arası bağlam sağlar
- 🌐 **Türkçe Odaklı**: Türkçe sokak dili, küfürlü ama sevimli kişilik
- ⚡ **Groq llama-3.3-70b-versatile**: Birincil AI (ücretsiz, hızlı)
- 📏 **Kısa Cevaplar**: 120 karakter hedef, 140 karakter platform limiti
- ⏰ **Gerçek Zamanlı**: Her soruda güncel Türkiye saati ve tarih bilgisi
- 🎨 **Modüler Yapı**: Kolay genişletilebilir modül sistemi
- 🔐 **Cloudflare Koruması**: Cloudflare korumalı sitelere bağlanabilir
- 🚫 **DM Yok**: Sadece oda mesajlarına cevap verir (DM'leri görmezden gelir)
- 👋 **Otomatik Selam**: Odaya katılan herkese hoş geldin mesajı gönderir
- 🛡️ **Owner Authentication**: Owner kullanıcısı için şifre doğrulama sistemi
- ⚙️ **Komut Sistemi**: !yardım, !saat, !unutbeni gibi kullanışlı komutlar
- 🚦 **Rate Limiting**: Kullanıcı başına dakikada 10 istek limiti
- 🧹 **Auto-Cleanup**: 1 saat inaktif kullanıcıların geçmişi otomatik temizlenir
- ✅ **Cevap Validasyon**: Her cevap kalite kontrolünden geçer
- 🔄 **Fallback Sistemi**: Geçersiz cevaplarda otomatik yedek yanıt
- 🚫 **Soru Yasağı**: Bot asla karşı soru sormaz, sadece cevap verir
- 👨‍👩‍👧 **Aile Sistemi**: aizen=baba, Days=abla olarak tanır
- ⚡ **Paralel İşleme**: Aynı anda birden fazla kullanıcıya cevap verebilir
- 🎬 **Özel Özellikler**: Film arama, hava durumu, döviz, zar, yazı-tura, matematik, Wikipedia

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

### 3. API Key'leri Alın (Ücretsiz!)

**Groq (Birincil AI):**
1. [console.groq.com](https://console.groq.com) adresine gidin
2. Ücretsiz hesap oluşturun
3. API Key oluşturun

### 4. .env Dosyası Oluşturun

Proje klasöründe `.env` dosyası oluşturun:

```env
# Groq API Key (birincil AI)
GROQ_API_KEY=gsk_your-groq-key-here

# Owner şifresi (aizen kullanıcısı için)
OWNER_PASSWORD=your_password

# Opsiyonel API Key'ler
WEATHER_API_KEY=your_weather_key
TMDB_API_KEY=your_tmdb_key
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
- ✅ Kısa ve öz cevaplar verir (max 120 karakter)
- ✅ Edgy, küfürlü ama sevimli kişilik (piç ama sevimli)
- ✅ Güncel tarih ve saat bilgisini bilir
- ✅ Her kullanıcı için konuşma geçmişi tutar (25 mesaj çifti)
- ✅ Oda sohbetini takip eder (kullanıcılar arası bağlam)
- ✅ Sadece Türkçe konuşur (İngilizce yazılsa bile)
- ✅ Odaya katılanlara otomatik selam verir
- ✅ "Sen kimsin?" gibi sorulara özel tanıtım yapar
- ✅ Aile sistemi: aizen=baba, Days=abla
- ✅ Film arama, hava durumu, döviz, matematik vb. özellikler
- ❌ DM (özel mesaj) kabul etmez
- 🔒 Owner authentication (aizen kullanıcısı için şifre doğrulama)

### Bot'u Durdurma

Terminal'de `Ctrl+C` ile bot'u güvenli şekilde kapatabilirsiniz.

## 🛠️ Özelleştirme

### AI Model Değiştirme

[modules/AIzen.py](modules/AIzen.py) dosyasında AI modelini değiştirebilirsiniz:

**AI Modelleri (Groq):**
- `llama-3.3-70b-versatile` - Güçlü ve doğal (ÖNERİLEN)
- `deepseek-r1-distill-llama-70b-specdec` - Hızlı ve kaliteli
- `llama-3.1-8b-instant` - Hızlı ve hafif

**Not:** Bot varsayılan olarak `llama-3.3-70b-versatile` kullanır.

### AI Personality Değiştirme

`modules/AIzen.py` içinde system prompt'u düzenleyin:

```python
self.system_prompt = """
Sen AI-zen. Özgüvenli, hafif ukala, piç ama sevimli birisin.
Türkçe sokak dili kullanırsın, küfür edebilirsin.
Max 120 karakter. 1-2 cümle ideal.
"""
```

### Karakter Limiti Ayarlama

Groq ayarları `modules/AIzen.py` içinde:

```python
self.model = "llama-3.3-70b-versatile"
self.max_tokens = 300
self.temperature = 0.8  # 0.0-2.0 (düşük=tutarlı, yüksek=yaratıcı)
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
**Çözüm:** `modules/AIzen.py` içinde model adını güncelleyin. Bot varsayılan olarak `llama-3.3-70b-versatile` kullanır.

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
**Çözüm:** Gerekli paketleri yükleyin:
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

### v1.3 - Mevcut Versiyon
- ✅ Groq llama-3.3-70b-versatile (birincil AI)
- ✅ Paralel mesaj işleme (eş zamanlı kullanıcı yanıtları)
- ✅ Oda sohbet farkındalığı (son 20 mesaj cross-user context)
- ✅ Per-user konuşma geçmişi (15 mesaj çifti)
- ✅ Edgy, piç ama sevimli Türkçe kişilik
- ✅ Sadece Türkçe konuşma kuralı (DİL KURALI)
- ✅ Aile sistemi: aizen=baba, Days=abla
- ✅ 120 karakter hedef limit
- ✅ Çift @username önleme
- ✅ Gönderici tanıma ([Yazan: @username])
- ✅ Film arama, hava durumu, döviz, matematik özellikleri

### Planlanmış Özellikler
- 🔄 7/24 cloud deployment (Fly.io/Railway)
- 🔄 Web dashboard (bot istatistikleri)
- 🔄 Çoklu oda desteği
- 🔄 Custom komutlar sistemi
- 🔄 Rate limit otomatik yönetimi

## 🙏 Teşekkürler

- [stozn/drrr-bot](https://github.com/stozn/drrr-bot) - Base bot implementasyonu
- [Groq](https://groq.com) - Birincil AI (ücretsiz)
- [drrr.com](https://drrr.com) - Chat platformu

## 📧 İletişim

Sorularınız için issue açabilirsiniz.

---

**[Groq](https://groq.com) - Ücretsiz AI. Sorumlu kullanın! 🎓
