# Katkıda Bulunma Rehberi

AI-zen projesine katkıda bulunmayı düşündüğünüz için teşekkür ederiz! 🎉

## İçindekiler

1. [Davranış Kuralları](#davranış-kuralları)
2. [Nasıl Katkı Yapabilirim](#nasıl-katkı-yapabilirim)
3. [Geliştirme Ortamı Kurulumu](#geliştirme-ortamı-kurulumu)
4. [Kod Standartları](#kod-standartları)
5. [Commit Mesajları](#commit-mesajları)
6. [Pull Request Süreci](#pull-request-süreci)
7. [Test Etme](#test-etme)

## Davranış Kuralları

### Temel İlkeler

- 🤝 Saygılı ve yapıcı iletişim
- 🌍 Kapsayıcı ve açık bir topluluk
- 📚 Yardımlaşma ve öğrenme odaklı
- 🚫 Spam, hakaret veya zararlı içerik yasak

## Nasıl Katkı Yapabilirim

### Hata Bildirimi 🐛

Bir hata bulduysanız:

1. **GitHub Issues** bölümüne gidin
2. Mevcut issue'larda arama yapın (duplicate önlemek için)
3. Yeni issue oluşturun ve şunları ekleyin:
   - Hata açıklaması
   - Tekrar etme adımları
   - Beklenen davranış vs gerçek davranış
   - Sistem bilgileri (Python versiyonu, OS, vb.)
   - Log çıktıları (varsa)

**Örnek:**
```markdown
## Hata Açıklaması
Bot @AI-zen etiketlemelerine cevap vermiyor

## Tekrar Etme
1. python main.py ile botu başlat
2. drrr.com odasında @AI-zen hello yaz
3. Bot cevap vermiyor

## Beklenen
Bot "Merhaba!" gibi bir cevap vermeli

## Sistem
- Python 3.12.2
- Windows 11
- Groq API key geçerli
```

### Özellik İsteği 💡

Yeni bir özellik öneriyorsanız:

1. **GitHub Issues** bölümünde "Feature Request" açın
2. Özelliğin amacını açıklayın
3. Kullanım senaryolarını belirtin
4. Varsa örnek kod gösterin

**Örnek:**
```markdown
## Özellik
Çoklu oda desteği

## Amaç
Bot'un aynı anda birden fazla odada olabilmesi

## Kullanım
config.txt:
roomIDs = room1,room2,room3

## Fayda
7/24 birden fazla odada hizmet verebilir
```

### Kod Katkısı 💻

1. **Fork** edin
2. **Branch** oluşturun (`git checkout -b feature/amazing-feature`)
3. **Değişiklikleri** yapın
4. **Test** edin
5. **Commit** edin (`git commit -m 'feat: Add amazing feature'`)
6. **Push** edin (`git push origin feature/amazing-feature`)
7. **Pull Request** açın

## Geliştirme Ortamı Kurulumu

### 1. Repository'yi Klonlayın

```bash
git clone https://github.com/yourusername/AIzen.git
cd AIzen
```

### 2. Python Environment Oluşturun (Opsiyonel ama Önerilir)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install aiohttp aiofiles curl_cffi groq python-dotenv
```

### 4. .env Dosyası Oluşturun

```env
GROQ_API_KEY=gsk_your_test_key_here
```

### 5. config.txt Ayarlayın

```txt
name = AIzen_Test
tc = None
avatar = setton
roomID = your_test_room_id
agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64)
mods = AIzen
throttle = 1.5
```

### 6. Test Edin

```bash
python main.py
```

## Kod Standartları

### Python Stil Rehberi

Bu proje için genel Python standartlarını takip ediyoruz:

#### 1. İsimlendirme

```python
# Classes: PascalCase
class MyModule(Module):
    pass

# Functions/Methods: snake_case
def get_ai_response(question):
    pass

# Constants: UPPER_SNAKE_CASE
MAX_HISTORY = 10
API_ENDPOINT = "https://api.groq.com"

# Variables: snake_case
user_name = "AIzen"
conversation_history = {}
```

#### 2. Docstrings

```python
def get_ai_response(self, question, user_id, user_name):
    """
    Groq API ile AI cevabı üretir
    
    Args:
        question (str): Kullanıcının sorusu
        user_id (str): Kullanıcı ID'si
        user_name (str): Kullanıcı adı
    
    Returns:
        str: AI'ın cevabı
    
    Raises:
        Exception: API hatası durumunda
    """
    pass
```

#### 3. Type Hints (Önerilir)

```python
from typing import List, Dict, Optional

def process_messages(messages: List[Dict]) -> Optional[str]:
    pass
```

#### 4. Error Handling

```python
# ✅ İyi
try:
    response = self.client.chat.completions.create(...)
except Exception as e:
    if "api_key" in str(e).lower():
        return "⚠️ API key hatası"
    elif "rate_limit" in str(e).lower():
        return "⚠️ Rate limit aşıldı"
    else:
        return f"⚠️ Hata: {str(e)[:100]}"

# ❌ Kötü
try:
    response = self.client.chat.completions.create(...)
except:
    return "Hata"
```

### Dil Kullanımı

- **Kod içi yorumlar**: Türkçe (proje Türk kullanıcılar için)
- **Değişken isimleri**: İngilizce (standart)
- **Kullanıcıya görünen mesajlar**: Türkçe
- **Dokümantasyon**: İngilizce (geniş erişim için)

```python
# Kullanıcı mesajını history'e ekle (Türkçe yorum)
self.conversation_history[user_id].append({  # İngilizce değişken
    "role": "user",
    "content": question
})

# Kullanıcıya Türkçe mesaj
return "⚠️ API key hatası. https://console.groq.com"
```

### Async/Await Kullanımı

```python
# ✅ İyi - async function
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ✅ Thread-safe async çağrı
asyncio.run_coroutine_threadsafe(self.putQ(msgs), self.loop)

# ❌ Kötü - blocking işlem async function içinde
async def bad_function():
    time.sleep(5)  # Bu blocking!
```

## Commit Mesajları

### Format

Conventional Commits standardını kullanıyoruz:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: Yeni özellik
- `fix`: Hata düzeltmesi
- `docs`: Dokümantasyon değişikliği
- `style`: Kod formatı (logic değişikliği yok)
- `refactor`: Kod refactor (özellik veya hata değil)
- `test`: Test ekleme/düzeltme
- `chore`: Build/config değişiklikleri

### Örnekler

```bash
# Yeni özellik
git commit -m "feat(ai): Add multi-language auto-detection"

# Hata düzeltmesi
git commit -m "fix(networking): Handle empty JSON responses"

# Dokümantasyon
git commit -m "docs(readme): Update installation instructions"

# Refactor
git commit -m "refactor(modules): Simplify command matching logic"

# Detaylı commit
git commit -m "feat(ai): Add conversation history per user

- Store last 10 messages per user ID
- Clear history when user leaves room
- Limit memory usage with max history

Closes #123"
```

## Pull Request Süreci

### 1. Pull Request Oluşturmadan Önce

- [ ] Kodunuz çalışıyor mu?
- [ ] Testler başarılı mı?
- [ ] Dokümantasyon güncellendi mi?
- [ ] Kod standartlarına uygun mu?
- [ ] Commit mesajları düzgün mü?

### 2. PR Açıklaması

**Şablon:**

```markdown
## Değişiklik Türü
- [ ] Hata düzeltmesi (fix)
- [ ] Yeni özellik (feature)
- [ ] Dokümantasyon
- [ ] Refactor

## Açıklama
Bu PR neyi değiştiriyor/ekliyor?

## Motivasyon ve Context
Neden bu değişiklik gerekli?

## Test Nasıl Yapıldı
- [ ] Test 1
- [ ] Test 2

## Screenshots (varsa)
[Ekran görüntüleri ekle]

## Checklist
- [ ] Kod standartlarına uygun
- [ ] Dokümantasyon güncellendi
- [ ] Testler başarılı
- [ ] Commit mesajları düzgün
```

### 3. Review Süreci

- Maintainer PR'ınızı inceleyecek
- Değişiklik talepleri olabilir
- Onaylandıktan sonra merge edilir

### 4. PR Kuralları

- Her PR bir şey yapmalı (single responsibility)
- Büyük değişiklikler küçük PR'lara bölünmeli
- WIP (Work in Progress) PR'lar draft olarak işaretlenmeli
- Conflictler merge edilmeden önce çözülmeli

## Test Etme

### Manuel Test Checklist

Değişiklik yaptıktan sonra:

- [ ] `python main.py` ile bot başlıyor
- [ ] Bot odaya giriş yapabiliyor
- [ ] `@AIzen test` mesajına cevap veriyor
- [ ] Cevaplar 140 karakterden kısa
- [ ] Türkçe dil kalitesi iyi
- [ ] Gerçek zamanlı tarih/saat bilgisi doğru
- [ ] DM'lere cevap vermiyor
- [ ] Hata durumlarında kullanıcı dostu mesaj
- [ ] Log dosyaları oluşuyor
- [ ] Terminal'de error yok

### Test Senaryoları

#### Senaryo 1: Temel Fonksiyonellik
```
1. Bot'u başlat
2. Odaya gir
3. "@AIzen merhaba" yaz
4. Bot cevap versin
5. Bot cevabı 140 karakterden kısa olmalı
```

#### Senaryo 2: Tarih/Saat
```
1. "@AIzen saat kaç" yaz
2. Bot güncel Türkiye saatini söylemeli
3. "@AIzen bugün günlerden ne" yaz
4. Bot doğru günü söylemeli
```

#### Senaryo 3: Konuşma Geçmişi
```
1. "@AIzen benim adım Alice" yaz
2. "@AIzen benim adımı hatırlıyor musun" yaz
3. Bot "Alice" diyerek hatırlamalı
```

#### Senaryo 4: Hata Durumları
```
1. .env dosyasında yanlış API key
2. Bot hata mesajı vermeli (crash olmamalı)
3. Kullanıcı dostu Türkçe hata mesajı olmalı
```

## Sorularınız mı Var?

- **GitHub Issues**: Teknik sorular için
- **Discussions**: Genel tartışmalar için
- **Email**: Gizli/hassas konular için

## Teşekkürler! 🙏

Katkınız için teşekkür ederiz. Her katkı, küçük veya büyük, projeyi daha iyi yapar! 🚀

---

**Son Güncelleme**: 22 Şubat 2026
