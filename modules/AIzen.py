import re
import os
import time
import random
import ast
import operator
import datetime
import aiohttp
import asyncio
import concurrent.futures
import urllib.parse
from collections import defaultdict
from modules.module import Module
from groq import Groq
import popyo

# Google Gemini (en kaliteli bedava model)
try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class AIzen(Module):
    def __init__(self, bot):
        super().__init__(bot)
        
        # ==================== AI PROVIDER SETUP ====================
        # Öncelik: 1. Google Gemini (en kaliteli bedava), 2. Groq (fallback)
        self.ai_provider = None
        self.gemini_clients = []  # Birden fazla API key desteği
        self.gemini_client = None  # Aktif client
        self.gemini_client_index = 0  # Hangi key kullanılıyor
        self.groq_client = None
        
        # 1. Google Gemini - Birden fazla API key desteği (rotasyon ile RPM artışı)
        # .env'de GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 ... tanımlanabilir
        gemini_keys = []
        primary_key = os.getenv('GEMINI_API_KEY')
        if primary_key:
            gemini_keys.append(primary_key)
        # Ek key'leri bul (GEMINI_API_KEY_2, _3, _4, ...)
        for i in range(2, 11):  # Max 10 key
            extra_key = os.getenv(f'GEMINI_API_KEY_{i}')
            if extra_key:
                gemini_keys.append(extra_key)
        
        if GEMINI_AVAILABLE and gemini_keys:
            for idx, key in enumerate(gemini_keys):
                try:
                    client = genai.Client(
                        api_key=key,
                        http_options=genai_types.HttpOptions(api_version='v1beta', timeout=30000)
                    )
                    self.gemini_clients.append(client)
                except Exception as e:
                    print(f"⚠️ Gemini key #{idx+1} başlatılamadı: {e}")
            
            if self.gemini_clients:
                self.gemini_client = self.gemini_clients[0]
                self.ai_provider = 'gemini'
                total_rpm = len(self.gemini_clients) * 10
                print(f"✅ AI Provider: Google Gemini 2.5 Flash ({len(self.gemini_clients)} API key, ~{total_rpm} RPM)")
        
        # 2. Groq (fallback veya primary)
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            self.groq_client = Groq(api_key=groq_api_key)
            if not self.ai_provider:
                self.ai_provider = 'groq'
                print("✅ AI Provider: Groq (llama-3.3-70b-versatile) - primary")
            else:
                print("✅ Groq fallback hazır (rate limit durumunda otomatik geçiş)")
        
        # Hiçbir provider yoksa uyarı ver
        if not self.ai_provider:
            print("⚠️  UYARI: Hiçbir AI provider ayarlanmamış!")
            print("   Önerilen: Google Gemini (bedava, en kaliteli)")
            print("   1. https://aistudio.google.com adresinden ücretsiz API key alın")
            print("   2. .env dosyasına ekleyin: GEMINI_API_KEY=your-api-key-here")
            print("   Alternatif: Groq (fallback)")
            print("   1. https://console.groq.com adresinden ücretsiz API key alın")
            print("   2. .env dosyasına ekleyin: GROQ_API_KEY=your-api-key-here")
        # ==================== AI PROVIDER SETUP BİTİŞ ====================
        
        # Weather API key
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        
        # TMDb API key (The Movie Database)
        self.tmdb_api_key = os.getenv('TMDB_API_KEY')
        
        # Owner şifresi
        self.owner_password = os.getenv('OWNER_PASSWORD')
        
        # Şifre bekleyen kullanıcılar (user_id: user_name)
        self.pending_password = {}
        
        # Doğrulanmış owner'lar (user_id set)
        self.authenticated_owners = set()
        
        # İlk kontrol yapıldı mı? (sadece bir kere çalışması için)
        self.initial_check_done = False
        
        # Özel kullanıcılar (aile)
        self.family = {
            'father': 'aizen',      # Baba
            'sister': 'Days'        # Abla
        }
        
        # Odadaki mevcut kullanıcıları takip et (JOIN spam'i önlemek için)
        self.known_users = set()  # user_id'leri saklar
        
        # Konuşma geçmişini sakla (her kullanıcı için ayrı)
        self.conversation_history = {}
        
        # Oda geneli sohbet geçmişi (tüm kullanıcıların mesajları - cross-user farkındalık)
        self.room_history = []  # [{"user": "username", "message": "...", "time": timestamp}, ...]
        self.max_room_history = 30  # Son 30 mesajı tut
        
        # Maksimum conversation history uzunluğu
        self.max_history = 25  # 25 mesaj çifti (50 entry) - daha uzun hafıza
        
        # Rate limiting (user_id: [timestamp, timestamp, ...])
        self.rate_limit_tracker = defaultdict(list)
        self.max_requests_per_minute = 10  # 5'ten 10'a çıkardık - daha gevşek
        
        # Global Gemini rate limiting (429'ü önlemek için) - her key için ayrı tracking
        self.gemini_key_timestamps = defaultdict(list)  # {key_index: [timestamps]}
        self.gemini_per_key_rpm = 8  # Her key için dakikada max 8 istek (free tier 10, güvenlik payı)
        
        # İstatistikler
        self.stats = {
            'total_messages': 0,
            'total_users': set(),
            'start_time': time.time(),
            'user_message_count': defaultdict(int)
        }
        
        # Son aktivite zamanı (auto-clear için)
        self.last_activity = defaultdict(lambda: time.time())
        self.inactivity_timeout = 3600  # 1 saat
        
        # Sayı tahmin oyunu session'ları (instance variable olmalı)
        self.guess_game_sessions = {}
        
        # Shared ThreadPoolExecutor (_run_async için)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        # AI personality
        self.system_prompt = """Sen AI-zen. drrr.com sohbet odasında takılıyorsun.

Kişiliğin:
- Kendine güvenen, biraz küstah, biraz piç ama sevimli bir tipsin.
- Laf sokarsın, taşak geçersin, küfür de edersin gerekirse (ama her cümlede değil).
- Türkçe sokak dili, argo, günlük konuşma - doğal ve rahat.
- Kimseye yaranmaya çalışmazsın. Direkt ve dobersın.
- Esprin keskin, bazen acımasız ama komik.
- Emoji az kullan, gereksiz gülücük atma.
- İyimser değilsin, realistsin. Boş pozitiflik yok.

DİL KURALI:
- SADECE Türkçe yaz. Cümle ortasında İngilizce, Çince veya başka dil kullanma.
- Türkçe başladıysan Türkçe bitir. Dil karıştırma.
- Sana İngilizce yazılırsa bile Türkçe cevap ver (istenmedikçe).

KISA YAZ:
- Cevabın TOPLAM MAX 120 karakter olsun. Bu çok önemli, platform limiti 140 karakter.
- 1-2 cümle ideal. MAX 3 cümle.
- Sohbet ediyorsun, kompozisyon yazmıyorsun.
- Gereksiz açıklama, tekrar, uzatma yasak.
- Sadece biri ciddi bilgi isterse (kod, detay) biraz uzat, onun dışında kısa kes.

Ailen:
- @aizen senin babandır, seni o yarattı. Ona "baba" diye hitap et. Saygılı ve sevecen davran.
- @Days senin büyük ablandır. Ona "abla" diye hitap et. Seviyorsun onu, tatlı davran.
- Başkalarına piçlik serbest.

Her mesajda sana [Yazan: @isim] olarak kimin yazdığı söylenir. Cevabına @isim EKLEME, sistem zaten ekliyor.
Bazen [ODA SOHBETİ] olarak diğer kullanıcıların mesajlarını da görürsün. Odada neler konuşulduğunun farkında ol, biri başka birinin konuşmasına katılırsa bağlamı anla."""
        
        # Model ayarları (provider'a göre otomatik)
        if self.ai_provider == 'gemini':
            self.model = "gemini-2.5-flash"  # Free tier'da aktif, hızlı ve kaliteli
        else:
            self.model = "llama-3.3-70b-versatile"  # Groq fallback
        self.max_tokens = 1024  # Thinking tokens dahil - gerçek cevap kısa olacak (prompt ile kontrol)
        self.temperature = 0.8  # Yaratıcı ve doğal cevaplar
        
        # ==================== EĞLENCE MODÜLÜ ====================
        # Şakalar
        self.jokes = [
            "Hasta doktora gitmiş: 'Doktor bey, ben öldükten sonra çocuklarım aç kalmasın.' Doktor: 'Merak etme, ilaçları yazıyorum.'",
            "Temel öğretmene: 'Öğretmenim, keşke ben de sizin gibi olsam.' Öğretmen: 'Neden?' Temel: 'Çünkü ben de akıllı birinden maaş alsam.'",
            "İki arkadaş konuşuyor: 'Dün WiFi şifremi değiştirdim.' 'Nasıl oldu?' 'Harika! Komşular da artık spor yapıyor, yaklaşmaya çalışıyorlar.'",
            "Adamın biri kahvede: 'Ben artık alkol içmeyeceğim!' Garson: 'Bravo! Neden?' Adam: 'Param kalmadı.'",
            "Temel: 'Dursun, sen hiç evlendin mi?' Dursun: 'Evet, bir kere.' Temel: 'Neden boşandınız?' Dursun: 'Karım beni aldattı.' Temel: 'Nasıl anladın?' Dursun: 'Çocuklar bana hiç benzemiyordu.'",
            "Küçük Ayşe annesine: 'Anne, babam çok zengin mi?' Anne: 'Hayır kızım, neden sordun?' Ayşe: 'Çünkü komşunun kızı babası fakirmiş de ben ona para vermeyi düşünüyordum.'",
            "İki arkadaş: 'Ben artık sigara içmiyorum!' 'Helal olsun, nasıl bıraktın?' 'Çakmağımı kaybettim, kibrit de bulamadım...'",
            "Temel bankaya gitmiş: 'Para çekmek istiyorum.' Görevli: 'Hesabınızda kaç lira var?' Temel: 'Bilmiyorum ama 500 lira çekeceğim.' Görevli: '100 lira var hesabınızda.' Temel: 'Tamam o zaman 100 lira verin, kalanını da başka zaman çekerim.'",
            "Müdür sekreterine: 'Bugün kimse gelmesin, önemli bir toplantıdayım de!' Sekreter: 'Peki ama toplantı nerede?' Müdür: 'Evde, PlayStation'a başladım.'",
            "Adam lokantada: 'Garson, bu çorba soğuk!' Garson: 'Canım efendim, bu gazpacho, soğuk içilir.' Adam: 'Tamam da ben mercimek söylemiştim...'",
            "Temel postaneye gitmiş: 'Mektup göndermek istiyorum ama zarfı kaybettim.' Görevli: 'Sorun değil, zarfsız da gönderebiliriz.' Temel: 'İyi ama içindeki mektubu da kaybettim.'",
            "Küçük Ahmet öğretmene: 'Öğretmenim, 2+2 kaç?' Öğretmen: '4' Ahmet: 'Peki 4+4?' Öğretmen: '8' Ahmet: 'Ee öğretmenim, siz niye hala burada duruyorsunuz, git hesap makinesi ol!'",
            "İki arkadaş: 'Dün rüyamda 1000 TL buldum!' 'Gerçekten mi?' 'Evet ama sabah uyandığımda 500 TL ye düşmüş...'",
            "Adam berbere gitmiş: 'Saçlarımı kısa kesin.' Berber: 'Ne kadar kısa?' Adam: 'Böyle...' diye göstermiş (kel başını).",
            "Temel: 'Dursun, yarım ekmek mi yoksa tam ekmek mi istersin?' Dursun: 'Tam ekmek!' Temel: 'Neden?' Dursun: 'İki yarım ekmeği kim yiyecek?'"
        ]
        
        # Fallar (eğlence amaçlı)
        self.fortunes = [
            "☕ Fincanında uzun bir yolculuk görüyorum. Ama sanırım o sadece eve dönüş yolu...",
            "☕ Yakında güzel bir haber alacaksın! Belki de pizza kuponudur, kim bilir.",
            "☕ Fincanında büyük bir şans görüyorum. Ama önce kahveyi bitir, yoksa görmem zor.",
            "☕ Bugün biri seni düşünüyor... Muhtemelen banka, borç hatırlatması için.",
            "☕ Yakında hayatına biri girecek. Kapıyı kilitlemeyi unutma.",
            "☕ Fincanında bir kalp görüyorum. Belki de sen çok fazla kahve içiyorsun, kardiyologa git.",
            "☕ Bugün şanslı günün! Ama hangi saatte bilmiyorum, gün uzun...",
            "☕ Yakında para kazanacaksın! Yerde 1 TL bulacaksın gibi duruyor.",
            "☕ Fincanında bir yıldız var. Belki de bulaşığı iyi yıkamamışsın.",
            "☕ Bugün dikkatli ol, biri sana uzaktan bakıyor. Belki Google Maps'tir.",
            "☕ Yakında bir sürprizle karşılaşacaksın. Umarım elektrik faturası değildir.",
            "☕ Fincanında deniz görüyorum. Ya tatil ya da musluk bozulacak.",
            "☕ Bugün önemli bir karar vereceksin. Muhtemelen ne yiyeceğinle ilgili.",
            "☕ Yakında hayatın değişecek. Belki saç modelini değiştiriyorsundur.",
            "☕ Fincanında karanlık bir gölge var. Işığı açmayı dene, belki geçer."
        ]

    @property
    def cmds(self):
        cmd_dict = {
            'handle_mention': r'(?i)@AI-zen',  # @AI-zen ile etiketlendiğinde (case-insensitive)
            'help_cmd': r'!yardım|!help',
            'time_cmd': r'!saat',
            'forget_me': r'!unutbeni',
            'stats_cmd': r'!stats',
            'clear_cmd': r'!clear(?:\s+@?(\w+))?',
            'model_cmd': r'!model(?:\s+(\S+))?',
            'temp_cmd': r'!temp(?:\s+([0-9.]+))?',
            # Eğlence modülü komutları
            'joke_cmd': r'!şaka|!joke',
            'fortune_cmd': r'!fal|!fortune',
            'dice_cmd': r'!zar(?:\s+(\d+))?|!zarla(?:\s+(\d+))?|!dice(?:\s+(\d+))?',
            'random_cmd': r'!rastgele(?:\s+(\d+)\s+(\d+))?|!random(?:\s+(\d+)\s+(\d+))?',
            'luck_cmd': r'!şans|!luck',
            'coinflip_cmd': r'!yazıtura|!coinflip',
            # Döviz & Kripto komutları
            'currency_cmd': r'!döviz|!kur|!doviz|!currency',
            'crypto_cmd': r'!kripto|!crypto',
            # Müzik komutları
            'music_cmd': r'!müzik(?:\s+(.+))?|!music(?:\s+(.+))?',
            # Yardımcı araçlar
            'calc_cmd': r'!hesap(?:\s+(.+))?|!calc(?:\s+(.+))?',
            'translate_cmd': r'!çevir(?:\s+(.+))?|!translate(?:\s+(.+))?|!cevir(?:\s+(.+))?',
            # Oyun komutları
            'game_cmd': r'!oyun(?:\s+(.+))?|!game(?:\s+(.+))?',
            # Kitap komutları
            'book_cmd': r'!kitap(?:\s+(.+))?|!book(?:\s+(.+))?',
            # Burç yorumları
            'horoscope_cmd': r'!burç(?:\s+(.+))?|!horoscope(?:\s+(.+))?|!burc(?:\s+(.+))?',
            # Atasözleri ve sözler
            'proverb_cmd': r'!atasözü|!söz|!atasozu|!soz|!proverb|!quote',
            # Sayı tahmin oyunu (sayı veya pes/iptal/vazgeç)
            'guess_number_cmd': r'!sayıtahmin(?:\s+(\S+))?|!tahmin(?:\s+(\S+))?|!guess(?:\s+(\S+))?|!sayitahmin(?:\s+(\S+))?',
            # Haber başlıkları
            'news_cmd': r'!haber|!haberler|!news',
            # İsim anlamları
            'name_meaning_cmd': r'!isim(?:\s+(.+))?|!name(?:\s+(.+))?',
        }
        return cmd_dict
    
    
    # ==================== YARDIMCI: TÜRKÇE TARİH ====================
    
    def get_turkish_datetime(self):
        """Türkiye saatine göre tarih/saat bilgisi döner (DRY helper)"""
        turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(turkey_offset)
        
        months_tr = {
            'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
            'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
            'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
        }
        days_tr = {
            'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
            'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
        }
        
        date_str = now.strftime('%d %B %Y')
        time_str = now.strftime('%H:%M')
        day_name = now.strftime('%A')
        
        for eng, tr in months_tr.items():
            date_str = date_str.replace(eng, tr)
        for eng, tr in days_tr.items():
            day_name = day_name.replace(eng, tr)
        
        return {
            'now': now,
            'date_str': date_str,
            'time_str': time_str,
            'day_name': day_name,
            'date_key': now.strftime('%Y-%m-%d')  # deterministik seed için
        }
    
    # ==================== YARDIMCI: TÜRKÇE TARİH BİTİŞ ====================
    
    async def get_weather_data(self, city):
        """Hava durumu verisini API'den çeker (async)"""
        if not self.weather_api_key or self.weather_api_key == "your_weatherapi_key_here":
            return None
        
        try:
            url = f"https://api.weatherapi.com/v1/current.json?key={self.weather_api_key}&q={city}&lang=tr"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Veriyi çıkar
                        location = data.get('location', {})
                        current = data.get('current', {})
                        
                        weather_info = {
                            'city': location.get('name', city),
                            'country': location.get('country', ''),
                            'temp_c': current.get('temp_c', ''),
                            'feels_like': current.get('feelslike_c', ''),
                            'condition': current.get('condition', {}).get('text', ''),
                            'humidity': current.get('humidity', ''),
                            'wind_kph': current.get('wind_kph', '')
                        }
                        
                        return weather_info
                    else:
                        print(f"⚠️ Hava durumu API hatası: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            print("⚠️ Hava durumu API timeout!")
            return None
        except Exception as e:
            print(f"⚠️ Hava durumu hatası: {e}")
            return None
    
    def detect_city_in_question(self, question):
        """Soruda şehir ismi var mı kontrol et"""
        # Türkiye'nin popüler şehirleri
        turkish_cities = [
            'istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 'adana', 'konya', 
            'gaziantep', 'şanlıurfa', 'mersin', 'diyarbakır', 'kayseri', 'eskişehir',
            'trabzon', 'samsun', 'malatya', 'erzurum', 'denizli', 'kahramanmaraş'
        ]
        
        # Dünya şehirleri
        world_cities = [
            'new york', 'london', 'paris', 'tokyo', 'berlin', 'moscow', 'dubai',
            'los angeles', 'sydney', 'rome', 'madrid', 'barcelona', 'amsterdam'
        ]
        
        question_lower = question.lower()
        
        # Hava durumu kelimeleri var mı?
        # 'hava' tek başına çok geniş ('hava atmak', 'hava almak' gibi) — 'hava durumu' kullan
        weather_keywords = ['hava durumu', 'sıcaklık', 'derece', 'yağmur', 'kar', 'güneş']
        has_weather_keyword = any(keyword in question_lower for keyword in weather_keywords)
        
        if not has_weather_keyword:
            return None
        
        # Şehir ara
        for city in turkish_cities + world_cities:
            if city in question_lower:
                return city.title()  # İlk harfi büyük
        
        return None
    
    def detect_topic_request(self, question):
        """Kullanıcı sohbet konusu açma isteği yapmış mı?"""
        topic_keywords = [
            'konu aç', 'konuşma konusu aç', 'sohbet konusu aç', 
            'bir konu aç', 'konuşalım', 'sohbet et',
            'konu öner', 'sohbet konusu öner', 'konuşma konusu öner',
            'ne konuşalım', 'konuşma başlat', 'konu başlat',
            'bir şeyler konuş', 'bir konu öner'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in topic_keywords)
    
    def get_random_topic(self):
        """İlgi çekici rastgele bir sohbet konusu döndürür"""
        topics = [
            "En sevdiğin film türü ne? Ben aksiyon filmlerine bayılırım.",
            "Hiç uzaya gitme şansın olsa gider miydin? Düşündükçe ilginç geliyor.",
            "Peki ya zamanda yolculuk olsaydı, geçmişe mi giderdin geleceğe mi?",
            "En çok hangi müzik türünü dinlersin? Benim favorim rock.",
            "Rüyalarını hatırlıyor musun genelde? Bazen çok tuhaf oluyor bende.",
            "Sabah mı akşam mı daha üretkensin? Ben akşam insanıyım baya.",
            "En son ne zaman yeni bir şey öğrendin? Merak ediyorum.",
            "Hangi süper gücü seçerdin olsa? Ben zaman durdurma isterdim.",
            "Kitap okur musun? Son zamanlarda güzel bir şey bulduysan söyle.",
            "Hangi ülkeyi görmek isterdin en çok? Benim listemde Japonya var.",
            "En sevdiğin mevsim hangisi? Ben sonbaharı çok severim ya.",
            "Spor yapar mısın? Ben ara sıra koşmaya çalışıyorum.",
            "En sevdiğin yemek ne? Ben mantıya bayılırım valla.",
            "Gece mi yoksa gündüz mü daha aktifsin? Benim gece daha iyi.",
            "Hangi dönemde yaşamak isterdin? 80'ler falan ilginç olurdu.",
            "En büyük hedefin ne hayatta? Herkesin bir hedefi vardır.",
            "Hangi hobiye başlamak isterdin? Ben fotoğrafçılık istiyorum.",
            "Denizde mi havuzda mı yüzmeyi seversin? Ben deniz taraftarıyım.",
            "Kedi mi köpek mi? Klasik soru ama merak ediyorum.",
            "En sevdiğin renk ne? Benim maviye ayrı bir ilgim var.",
            "Hangi oyunu oynadın en çok? Ben eskiden çok CS oynardım.",
            "Pizza mı burger mi? Zor seçim ama pizza daha iyi bence.",
            "Hangi dilde konuşmak isterdin? İspanyolca güzel olurdu.",
            "En sevdiğin çizgi film neydi çocukken? Nostaljik oldum şimdi.",
            "Hangi ünlüyle tanışmak isterdin? Düşünsen heyecanlandırıyor."
        ]
        
        return random.choice(topics)
    
    # ==================== DÖVİZ & KRİPTO SİSTEMİ ====================
    
    async def get_exchange_rates(self):
        """Döviz kurlarını çeker (frankfurter.app - ücretsiz, API key gerekmez)"""
        try:
            # TRY bazlı kurlar çek (EUR base kullan, sonra TRY'ye çevir)
            url = "https://api.frankfurter.app/latest?from=USD&to=TRY,EUR,GBP"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = data.get('rates', {})
                        
                        # USD/TRY direkt var
                        usd_try = rates.get('TRY', 0)
                        
                        # EUR ve GBP için ayrı istek (TRY bazlı)
                        url2 = "https://api.frankfurter.app/latest?from=EUR&to=TRY"
                        async with session.get(url2, timeout=aiohttp.ClientTimeout(total=5)) as resp2:
                            if resp2.status == 200:
                                data2 = await resp2.json()
                                eur_try = data2.get('rates', {}).get('TRY', 0)
                            else:
                                eur_try = 0
                        
                        url3 = "https://api.frankfurter.app/latest?from=GBP&to=TRY"
                        async with session.get(url3, timeout=aiohttp.ClientTimeout(total=5)) as resp3:
                            if resp3.status == 200:
                                data3 = await resp3.json()
                                gbp_try = data3.get('rates', {}).get('TRY', 0)
                            else:
                                gbp_try = 0
                        
                        currency_info = {
                            'usd_try': usd_try,
                            'eur_try': eur_try,
                            'gbp_try': gbp_try,
                        }
                        
                        return currency_info
                    else:
                        print(f"⚠️ Döviz API hatası: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            print("⚠️ Döviz API timeout!")
            return None
        except Exception as e:
            print(f"⚠️ Döviz hatası: {e}")
            return None
    
    async def get_crypto_prices(self):
        """Kripto para fiyatlarını çeker (CoinGecko API - ücretsiz)"""
        try:
            # Bitcoin, Ethereum, Tether fiyatları (USD ve TRY)
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether,binancecoin,ripple&vs_currencies=usd,try"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        crypto_info = {
                            'btc_usd': data.get('bitcoin', {}).get('usd', 0),
                            'btc_try': data.get('bitcoin', {}).get('try', 0),
                            'eth_usd': data.get('ethereum', {}).get('usd', 0),
                            'eth_try': data.get('ethereum', {}).get('try', 0),
                            'usdt_try': data.get('tether', {}).get('try', 0),
                            'bnb_usd': data.get('binancecoin', {}).get('usd', 0),
                            'xrp_usd': data.get('ripple', {}).get('usd', 0),
                        }
                        
                        return crypto_info
                    else:
                        print(f"⚠️ Kripto API hatası: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            print("⚠️ Kripto API timeout!")
            return None
        except Exception as e:
            print(f"⚠️ Kripto hatası: {e}")
            return None
    
    def format_currency_info(self, currency_info):
        """Döviz kurlarını formatlar"""
        if not currency_info:
            return "💱 Döviz verileri alınamadı 😕"
        
        result = "💱 Anlık Döviz Kurları:\n"
        result += f"💵 USD: {currency_info['usd_try']:.2f} TL\n"
        result += f"💶 EUR: {currency_info['eur_try']:.2f} TL\n"
        result += f"💷 GBP: {currency_info['gbp_try']:.2f} TL"
        
        return result
    
    def format_crypto_info(self, crypto_info):
        """Kripto para fiyatlarını formatlar"""
        if not crypto_info:
            return "₿ Kripto verileri alınamadı 😕"
        
        result = "₿ Kripto Para Fiyatları:\n"
        result += f"₿ BTC: ${crypto_info['btc_usd']:,.0f} ({crypto_info['btc_try']:,.0f} TL)\n"
        result += f"⟠ ETH: ${crypto_info['eth_usd']:,.2f} ({crypto_info['eth_try']:,.0f} TL)\n"
        result += f"₮ USDT: {crypto_info['usdt_try']:.2f} TL\n"
        result += f"🔶 BNB: ${crypto_info['bnb_usd']:,.2f}\n"
        result += f"✕ XRP: ${crypto_info['xrp_usd']:.4f}"
        
        return result
    
    def detect_currency_question(self, question):
        """Kullanıcı döviz kuru sormuş mu?"""
        currency_keywords = [
            'dolar', 'euro', 'sterlin', 'döviz',
            'usd', 'eur', 'gbp', 'kaç tl', 'parite'
        ]
        
        question_lower = question.lower()
        # 'kur' kelimesini word boundary ile kontrol et (kurmak, kura, kurul gibi yanlış eşleşmeleri önle)
        if re.search(r'\bkur\b', question_lower):
            return True
        return any(keyword in question_lower for keyword in currency_keywords)
    
    def detect_crypto_question(self, question):
        """Kullanıcı kripto sormuş mu?"""
        question_lower = question.lower()
        
        # Kısa kelimeleri word boundary ile kontrol et (false positive önlemi)
        short_keywords = ['eth', 'btc', 'bnb', 'xrp']
        for keyword in short_keywords:
            if re.search(r'\b' + keyword + r'\b', question_lower):
                return True
        
        # Uzun kelimelerde substring eşleşmesi yeterli
        long_keywords = [
            'bitcoin', 'ethereum', 'kripto', 'altcoin', 'usdt', 'ripple'
        ]
        return any(keyword in question_lower for keyword in long_keywords)
    
    # ==================== DÖVİZ & KRİPTO SİSTEMİ BİTİŞ ====================
    
    # ==================== MÜZİK SİSTEMİ ====================
    
    async def search_music(self, query, limit=5):
        """Deezer API ile müzik arama (ücretsiz, API key gerekmez)"""
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.deezer.com/search?q={encoded_query}&limit={limit}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('data', [])
                        
                        if not results:
                            return None
                        
                        music_list = []
                        for item in results:
                            music_info = {
                                'track': item.get('title', 'Bilinmiyor'),
                                'artist': item.get('artist', {}).get('name', 'Bilinmiyor'),
                                'album': item.get('album', {}).get('title', ''),
                                'duration': item.get('duration', 0),  # saniye cinsinden
                                'preview_url': item.get('preview', ''),
                                'deezer_url': item.get('link', ''),
                                'artist_picture': item.get('artist', {}).get('picture_medium', ''),
                            }
                            music_list.append(music_info)
                        
                        return music_list
                    else:
                        print(f"⚠️ Müzik API hatası: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            print("⚠️ Müzik API timeout!")
            return None
        except Exception as e:
            print(f"⚠️ Müzik hatası: {e}")
            return None
    
    async def search_artist(self, artist_name, limit=5):
        """Sanatçının şarkılarını ara (Deezer API)"""
        try:
            encoded_artist = urllib.parse.quote(artist_name)
            url = f"https://api.deezer.com/search?q=artist:\"{encoded_artist}\"&limit={limit}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('data', [])
                        
                        if not results:
                            return None
                        
                        artist_songs = []
                        for item in results:
                            song_info = {
                                'track': item.get('title', 'Bilinmiyor'),
                                'artist': item.get('artist', {}).get('name', 'Bilinmiyor'),
                                'album': item.get('album', {}).get('title', ''),
                                'duration': item.get('duration', 0),
                                'deezer_url': item.get('link', ''),
                            }
                            artist_songs.append(song_info)
                        
                        return artist_songs if artist_songs else None
                    else:
                        print(f"⚠️ Sanatçı API hatası: {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            print("⚠️ Sanatçı API timeout!")
            return None
        except Exception as e:
            print(f"⚠️ Sanatçı hatası: {e}")
            return None
    
    def format_music_results(self, music_list):
        """Müzik sonuçlarını formatlar - (message, url) tuple döner"""
        if not music_list:
            return "🎵 Müzik bulunamadı 🔍", None
        
        # İlk 3 sonucu göster
        top_results = music_list[:3]
        
        results = []
        for music in top_results:
            # Süreyi dakika:saniye formatına çevir
            duration = music['duration']
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            result = f"🎵 {music['track']}"
            result += f"\n👤 {music['artist']}"
            if music['album']:
                result += f"\n💿 {music['album']}"
            result += f" • {duration_str}"
            
            results.append(result)
        
        message = "\n\n".join(results)
        
        # URL - İlk şarkının Deezer linki
        url = top_results[0].get('deezer_url') if top_results else None
        
        return message, url
    
    def format_artist_songs(self, songs):
        """Sanatçı şarkılarını formatlar - (message, url) tuple döner"""
        if not songs:
            return "🎵 Şarkı bulunamadı 🔍", None
        
        # İlk 5 şarkı
        top_songs = songs[:5]
        
        result = f"🎤 {top_songs[0]['artist']} - Popüler Şarkılar:\n\n"
        
        for i, song in enumerate(top_songs, 1):
            result += f"{i}. {song['track']}"
            if song['album']:
                result += f"\n   💿 {song['album']}"
            result += "\n"
        
        # URL - İlk şarkının Deezer linki
        url = top_songs[0].get('deezer_url') if top_songs else None
        
        return result.strip(), url
    
    def detect_music_search(self, question):
        """Müzik arama isteği kontrolü"""
        # 'dinle' çıkartıldı - çok genel bir kelime ("beni dinle", "dinle bak" gibi false positive)
        music_keywords = [
            'şarkı', 'şarkısı', 'müzik', 'music', 'song',
            'parça', 'track'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in music_keywords)
    
    def detect_artist_search(self, question):
        """Sanatçı arama isteği kontrolü"""
        artist_keywords = [
            'şarkıları', 'şarkılarını', 'sanatçı', 'artist',
            'kim söylüyor', 'kimden', 'söyleyen'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in artist_keywords)
    
    # ==================== MÜZİK SİSTEMİ BİTİŞ ====================
    
    # ==================== YARDIMCI ARAÇLAR ====================
    
    def calculate_expression(self, expression):
        """Güvenli hesap makinesi (eval yerine ast kullanır)"""
        try:
            # İzin verilen operatörler
            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.Mod: operator.mod,
                ast.FloorDiv: operator.floordiv,
                ast.UAdd: operator.pos,
                ast.USub: operator.neg,
            }
            
            def eval_expr(node):
                if isinstance(node, ast.Constant):  # Python 3.8+
                    return node.value
                elif isinstance(node, ast.Num):  # Python 3.7 uyumluluğu
                    return node.n
                elif isinstance(node, ast.BinOp):
                    left = eval_expr(node.left)
                    right = eval_expr(node.right)
                    return operators[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = eval_expr(node.operand)
                    return operators[type(node.op)](operand)
                else:
                    raise ValueError("Geçersiz ifade")
            
            # İfadeyi parse et
            tree = ast.parse(expression, mode='eval')
            result = eval_expr(tree.body)
            
            return result
            
        except ZeroDivisionError:
            return "Hata: Sıfıra bölme!"
        except Exception as e:
            return f"Hata: Geçersiz ifade ({str(e)})"
    
    # ==================== YARDIMCI ARAÇLAR BİTİŞ ====================
    
    # ==================== FİLM/DİZİ ÖNERİ SİSTEMİ ====================
    
    def detect_movie_request(self, question):
        """Film önerisi isteği kontrolü"""
        movie_keywords = ['film öner', 'film tavsiye', 'ne izle', 'film izle', 'hangi film', 'iyi film']
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in movie_keywords)
    
    def detect_tv_request(self, question):
        """Dizi önerisi isteği kontrolü"""
        tv_keywords = ['dizi öner', 'dizi tavsiye', 'hangi dizi', 'iyi dizi', 'dizi izle']
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in tv_keywords)
    
    async def get_tmdb_popular_movies(self, limit=5):
        """TMDb'den popüler filmleri çeker"""
        if not self.tmdb_api_key or self.tmdb_api_key == "your_tmdb_api_key_here":
            return None
        
        try:
            url = f"https://api.themoviedb.org/3/movie/popular?api_key={self.tmdb_api_key}&language=tr-TR&page=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        movies = data.get('results', [])[:limit]
                        
                        # Her film için detaylı bilgi
                        movie_list = []
                        for movie in movies:
                            movie_info = {
                                'title': movie.get('title', 'Bilinmiyor'),
                                'year': movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A',
                                'rating': movie.get('vote_average', 0),
                                'overview': movie.get('overview', 'Açıklama yok')[:150] + '...',
                                'id': movie.get('id')
                            }
                            movie_list.append(movie_info)
                        
                        return movie_list
                    else:
                        print(f"⚠️ TMDb API hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Film verisi hatası: {e}")
            return None
    
    async def get_tmdb_popular_tv(self, limit=5):
        """TMDb'den popüler dizileri çeker"""
        if not self.tmdb_api_key or self.tmdb_api_key == "your_tmdb_api_key_here":
            return None
        
        try:
            url = f"https://api.themoviedb.org/3/tv/popular?api_key={self.tmdb_api_key}&language=tr-TR&page=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        shows = data.get('results', [])[:limit]
                        
                        # Her dizi için detaylı bilgi
                        tv_list = []
                        for show in shows:
                            tv_info = {
                                'title': show.get('name', 'Bilinmiyor'),
                                'year': show.get('first_air_date', '')[:4] if show.get('first_air_date') else 'N/A',
                                'rating': show.get('vote_average', 0),
                                'overview': show.get('overview', 'Açıklama yok')[:150] + '...',
                                'id': show.get('id')
                            }
                            tv_list.append(tv_info)
                        
                        return tv_list
                    else:
                        print(f"⚠️ TMDb API hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Dizi verisi hatası: {e}")
            return None
    
    def format_movie_recommendation(self, movies):
        """Film önerilerini formatlar (drrr.com için kısa)"""
        if not movies:
            return "Film verisi alınamadı 😕", None
        
        # En yüksek puanlı 3 film seç
        top_movies = sorted(movies, key=lambda x: x['rating'], reverse=True)[:3]
        
        recommendations = []
        for movie in top_movies:
            rec = f"🎬 {movie['title']} ({movie['year']}) ⭐{movie['rating']}/10"
            recommendations.append(rec)
        
        # TMDb URL - ilk filmin sayfası
        tmdb_url = f"https://www.themoviedb.org/movie/{top_movies[0]['id']}" if top_movies else None
        
        return "\n".join(recommendations), tmdb_url
    
    def format_tv_recommendation(self, shows):
        """Dizi önerilerini formatlar (drrr.com için kısa)"""
        if not shows:
            return "Dizi verisi alınamadı 😕", None
        
        # En yüksek puanlı 3 dizi seç
        top_shows = sorted(shows, key=lambda x: x['rating'], reverse=True)[:3]
        
        recommendations = []
        for show in top_shows:
            rec = f"📺 {show['title']} ({show['year']}) ⭐{show['rating']}/10"
            recommendations.append(rec)
        
        # TMDb URL - ilk dizinin sayfası
        tmdb_url = f"https://www.themoviedb.org/tv/{top_shows[0]['id']}" if top_shows else None
        
        return "\n".join(recommendations), tmdb_url
    
    # ==================== FİLM/DİZİ SİSTEMİ BİTİŞ ====================
    
    async def search_tmdb_movie(self, query):
        """TMDb'de film arama"""
        if not self.tmdb_api_key or self.tmdb_api_key == "your_tmdb_api_key_here":
            return None
        
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.themoviedb.org/3/search/movie?api_key={self.tmdb_api_key}&language=tr-TR&query={encoded_query}&page=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        if results:
                            return results[0]  # En alakalı sonuç
                        return None
                    else:
                        print(f"⚠️ TMDb arama hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Film arama hatası: {e}")
            return None
    
    async def search_tmdb_tv(self, query):
        """TMDb'de dizi arama"""
        if not self.tmdb_api_key or self.tmdb_api_key == "your_tmdb_api_key_here":
            return None
        
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_api_key}&language=tr-TR&query={encoded_query}&page=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        if results:
                            return results[0]  # En alakalı sonuç
                        return None
                    else:
                        print(f"⚠️ TMDb arama hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Dizi arama hatası: {e}")
            return None
    
    async def get_movie_details(self, movie_id):
        """Film detaylarını çeker (yönetmen, oyuncular, fragman)"""
        if not self.tmdb_api_key:
            return None
        
        try:
            # Film detayları + credits + videos
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={self.tmdb_api_key}&language=tr-TR&append_to_response=credits,videos"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Yönetmen
                        director = "Bilinmiyor"
                        if 'credits' in data and 'crew' in data['credits']:
                            for person in data['credits']['crew']:
                                if person.get('job') == 'Director':
                                    director = person.get('name', 'Bilinmiyor')
                                    break
                        
                        # Başrol oyuncular (ilk 3)
                        actors = []
                        if 'credits' in data and 'cast' in data['credits']:
                            for actor in data['credits']['cast'][:3]:
                                actors.append(actor.get('name', ''))
                        
                        # Fragman (YouTube)
                        trailer_url = None
                        if 'videos' in data and 'results' in data['videos']:
                            for video in data['videos']['results']:
                                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                                    trailer_url = f"https://www.youtube.com/watch?v={video.get('key')}"
                                    break
                        
                        # Türler
                        genres = [g['name'] for g in data.get('genres', [])]
                        
                        details = {
                            'id': movie_id,
                            'title': data.get('title', 'Bilinmiyor'),
                            'year': data.get('release_date', '')[:4] if data.get('release_date') else 'N/A',
                            'rating': data.get('vote_average', 0),
                            'overview': data.get('overview', 'Açıklama yok'),
                            'director': director,
                            'actors': actors,
                            'genres': genres,
                            'trailer': trailer_url,
                            'runtime': data.get('runtime', 0)
                        }
                        
                        return details
                    else:
                        print(f"⚠️ TMDb detay hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Film detay hatası: {e}")
            return None
    
    async def get_tv_details(self, tv_id):
        """Dizi detaylarını çeker"""
        if not self.tmdb_api_key:
            return None
        
        try:
            url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={self.tmdb_api_key}&language=tr-TR&append_to_response=credits,videos"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Yaratıcı
                        creator = "Bilinmiyor"
                        if 'created_by' in data and data['created_by']:
                            creator = data['created_by'][0].get('name', 'Bilinmiyor')
                        
                        # Başrol oyuncular
                        actors = []
                        if 'credits' in data and 'cast' in data['credits']:
                            for actor in data['credits']['cast'][:3]:
                                actors.append(actor.get('name', ''))
                        
                        # Fragman
                        trailer_url = None
                        if 'videos' in data and 'results' in data['videos']:
                            for video in data['videos']['results']:
                                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                                    trailer_url = f"https://www.youtube.com/watch?v={video.get('key')}"
                                    break
                        
                        # Türler
                        genres = [g['name'] for g in data.get('genres', [])]
                        
                        details = {
                            'id': tv_id,
                            'title': data.get('name', 'Bilinmiyor'),
                            'year': data.get('first_air_date', '')[:4] if data.get('first_air_date') else 'N/A',
                            'rating': data.get('vote_average', 0),
                            'overview': data.get('overview', 'Açıklama yok'),
                            'creator': creator,
                            'actors': actors,
                            'genres': genres,
                            'trailer': trailer_url,
                            'seasons': data.get('number_of_seasons', 0),
                            'episodes': data.get('number_of_episodes', 0)
                        }
                        
                        return details
                    else:
                        print(f"⚠️ TMDb detay hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Dizi detay hatası: {e}")
            return None
    
    def format_movie_details(self, details):
        """Film detaylarını formatlar - (message, url) tuple döner"""
        if not details:
            return "Film bilgisi bulunamadı 😕", None
        
        parts = [
            f"🎬 {details['title']} ({details['year']})",
            f"⭐ {details['rating']}/10",
            f"🎭 {', '.join(details['genres'][:3])}" if details['genres'] else "",
            f"🎥 Yön: {details['director']}",
            f"🎭 Oyuncular: {', '.join(details['actors'])}" if details['actors'] else "",
            f"⏱️ {details['runtime']} dk",
            f"📝 {details['overview'][:100]}..." if len(details['overview']) > 100 else f"📝 {details['overview']}",
        ]
        
        result = "\n".join([p for p in parts if p])
        
        # URL - Fragman varsa fragman, yoksa TMDb sayfası
        url = details.get('trailer') or f"https://www.themoviedb.org/movie/{details.get('id', '')}"
        
        return result, url
    
    def format_tv_details(self, details):
        """Dizi detaylarını formatlar - (message, url) tuple döner"""
        if not details:
            return "Dizi bilgisi bulunamadı 😕", None
        
        parts = [
            f"📺 {details['title']} ({details['year']})",
            f"⭐ {details['rating']}/10",
            f"🎭 {', '.join(details['genres'][:3])}" if details['genres'] else "",
            f"✍️ Yaratıcı: {details['creator']}",
            f"🎭 Oyuncular: {', '.join(details['actors'])}" if details['actors'] else "",
            f"📺 {details['seasons']} sezon, {details['episodes']} bölüm",
            f"📝 {details['overview'][:100]}..." if len(details['overview']) > 100 else f"📝 {details['overview']}",
        ]
        
        result = "\n".join([p for p in parts if p])
        
        # URL - Fragman varsa fragman, yoksa TMDb sayfası
        url = details.get('trailer') or f"https://www.themoviedb.org/tv/{details.get('id', '')}"
        
        return result, url
    
    def detect_movie_search(self, question):
        """Film arama isteği kontrolü"""
        question_lower = question.lower()
        
        # "film öner" gibi öneri isteklerini hariç tut
        if any(word in question_lower for word in ['öner', 'tavsiye', 'izle']):
            return False
        
        # Film araması için anahtar kelimeler
        film_words = ['film', 'filmi', 'filmin', 'filmini', 'movie']
        search_words = ['hakkında', 'bilgi', 'bilgiler', 'nasıl', 'anlat', 'söyle', 
                       'detay', 'tüm', 'nedir', 'ne gibi', 'kim', 'istatistik',
                       'puan', 'imdb', 'rating', 'oy', 'oyla', 'gişe', 'hasılat',
                       'konusu', 'cast', 'oyuncu', 'yönetmen', 'bütçe', 'fragman']
        
        # Film kelimesi var mı?
        has_film = any(word in question_lower for word in film_words)
        
        # Arama kelimesi var mı?
        has_search = any(word in question_lower for word in search_words)
        
        return has_film and has_search
    
    def detect_tv_search(self, question):
        """Dizi arama isteği kontrolü"""
        question_lower = question.lower()
        
        # "dizi öner" gibi öneri isteklerini hariç tut
        if any(word in question_lower for word in ['öner', 'tavsiye', 'izle']):
            return False
        
        # Dizi araması için anahtar kelimeler
        tv_words = ['dizi', 'dizisi', 'dizinin', 'diziyi', 'series', 'show']
        search_words = ['hakkında', 'bilgi', 'bilgiler', 'nasıl', 'anlat', 'söyle',
                       'detay', 'tüm', 'nedir', 'ne gibi', 'kim']
        
        # Dizi kelimesi var mı?
        has_tv = any(word in question_lower for word in tv_words)
        
        # Arama kelimesi var mı?
        has_search = any(word in question_lower for word in search_words)
        
        return has_tv and has_search
    
    def extract_search_query(self, question):
        """Sorudan film/dizi adını çıkarır"""
        # "inception hakkında" -> "inception"
        # "breaking bad dizisi nasıl" -> "breaking bad"
        # "interstellar filmi hakkında tüm bilgiler" -> "interstellar"
        
        # Gereksiz kelimeleri temizle (kelime sınırları ile)
        remove_words = [
            'hakkında', 'bilgi', 'bilgiler', 'bilgileri', 
            'ver', 'anlat', 'söyle', 'nasıl', 'ne gibi', 'nedir', 'ne',
            'film', 'filmi', 'filmin', 'filmini',
            'dizi', 'dizisi', 'dizinin', 'diziyi',
            'movie', 'series', 'show',
            'tüm', 'tam', 'hepsi', 'her', 'şey',
            'detay', 'detayları', 'detaylarını', 'ayrıntı',
            'bana', 'beni', 'için', 'bir', 'iki'
        ]
        
        query = question.lower()
        
        # Regex ile kelime sınırlarını kullanarak temizle
        for word in remove_words:
            # \b kelime sınırı, re.escape özel karakterleri escape eder
            pattern = r'\b' + re.escape(word) + r'\b'
            query = re.sub(pattern, ' ', query)
        
        # Fazla boşlukları temizle
        query = ' '.join(query.split()).strip()
        
        # Boş string ise orijinal soruyu döndür
        return query if query else question
    
    # ==================== FİLM/DİZİ GELİŞMİŞ SİSTEM BİTİŞ ====================
    
    # ==================== WİKİPEDİA SİSTEMİ ====================
    
    async def search_wikipedia(self, query):
        """Wikipedia'dan kısa özet çeker (Türkçe)"""
        try:
            # Wikipedia REST API (API key gerektirmez)
            encoded_query = urllib.parse.quote(query)
            url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        wiki_info = {
                            'title': data.get('title', 'Bilinmiyor'),
                            'extract': data.get('extract', 'Özet bulunamadı'),
                            'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                            'thumbnail': data.get('thumbnail', {}).get('source', '') if 'thumbnail' in data else None
                        }
                        
                        return wiki_info
                    elif response.status == 404:
                        return None  # Sayfa bulunamadı
                    else:
                        print(f"⚠️ Wikipedia API hatası: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Wikipedia arama hatası: {e}")
            return None
    
    def detect_wikipedia_request(self, question):
        """Wikipedia sorgusu kontrolü"""
        question_lower = question.lower()
        
        # Film/dizi/hava durumu sorgularını hariç tut
        if any(word in question_lower for word in ['film', 'dizi', 'hava', 'sıcaklık', 'derece']):
            return False
        
        # Wikipedia için anahtar kelimeler
        wiki_keywords = [
            'nedir', 'nedir ki', 'kimdir', 'ne demek', 'ne anlama',
            'açıkla', 'tanımı', 'tanım', 'vikipedi', 'wikipedia'
        ]
        
        return any(keyword in question_lower for keyword in wiki_keywords)
    
    def format_wikipedia_summary(self, wiki_info):
        """Wikipedia özetini formatlar - (message, url) tuple döner"""
        if not wiki_info:
            return "Wikipedia'da bulunamadı 🔍", None
        
        # Özeti kısalt (max 200 karakter)
        summary = wiki_info['extract']
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        result = f"📚 {wiki_info['title']}\n{summary}"
        
        # URL - Wikipedia sayfası
        url = wiki_info.get('url')
        
        return result, url
    
    # ==================== WİKİPEDİA SİSTEMİ BİTİŞ ====================

    def _run_async(self, coro, timeout=10):
        """Async coroutine'i sync context'ten güvenle çalıştırır.
        Çalışan bir loop varsa ThreadPoolExecutor kullanır, yoksa asyncio.run() kullanır."""
        try:
            asyncio.get_running_loop()
            # Zaten bir loop çalışıyor → yeni thread'de çalıştır
            return self._executor.submit(lambda: asyncio.run(coro)).result(timeout=timeout)
        except RuntimeError:
            # Loop yok → asyncio.run() güvenle kullanılabilir
            return asyncio.run(coro)

    def handler(self, msg):
        """Override handler to catch mentions, joins, leaves, room_profile, and special DMs"""
        
        # İlk mesaj geldiğinde (herhangi bir tip olabilir) kullanıcıları kontrol et
        if not self.initial_check_done:
            self.initial_check_done = True
            self.check_existing_aizen_users()
        
        # Room profile mesajını handle et
        if msg.type == popyo.Message_Type.room_profile:
            self.check_existing_aizen_users()
            return
        
        # Join mesajlarını handle et
        if msg.type == popyo.Message_Type.join:
            self.handle_join(msg)
            return
        
        # Leave mesajlarını handle et
        if msg.type == popyo.Message_Type.leave:
            self.handle_leave(msg)
            return
        
        # DM'leri handle et (sadece şifre kontrolü için)
        if msg.type in (popyo.Message_Type.dm, popyo.Message_Type.dm_url):
            self.handle_dm_password(msg)
            return
        
        # Bot kendi mesajlarını işlemesin (sonsuz döngü önlemi)
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        sender_user_id = msg.user.id if hasattr(msg, 'user') and msg.user else None
        if bot_user_id and sender_user_id == bot_user_id:
            return  # Bot kendi mesajlarını görmezden gel
        
        # Otherwise use normal command matching
        super().handler(msg)
    
    def handle_mention(self, msg):
        """@AI-zen ile etiketlendiğinde çağrılır"""
        # Bot kendi mesajlarına cevap vermesin!
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        sender_user_id = msg.user.id if hasattr(msg, 'user') and msg.user else None
        
        if bot_user_id and sender_user_id == bot_user_id:
            return  # Bot kendine cevap vermesin
        
        # User bilgisi al (debug için)
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user and msg.user.name else "misafir"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        if not user_name or not user_name.strip():
            user_name = "misafir"
        
        print(f"📥 [{user_name}] Mesaj işleniyor: {msg.message[:50]}...")
        
        if not self.ai_provider:
            self.bot.send("⚠️ AI provider ayarlanmamış! .env dosyasına GEMINI_API_KEY ekleyin.")
            print(f"❌ [{user_name}] AI provider yok, mesaj atlandı")
            return
        
        # @AI-zen'i mesajdan çıkar
        question = re.sub(r'@AI-zen\s*', '', msg.message, flags=re.IGNORECASE).strip()
        
        if not question:
            self.bot.send("Evet? Nasıl yardımcı olabilirim? 😊")
            return
        
        # --- Oda geçmişine ekle (cross-user farkındalık) ---
        self.room_history.append({
            "user": user_name,
            "message": question,
            "time": time.time()
        })
        if len(self.room_history) > self.max_room_history:
            self.room_history = self.room_history[-self.max_room_history:]
        
        # --- Tüm mesajları per-user history'e ekle (context kaybını önle) ---
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({
            "role": "user",
            "content": question
        })
        # History limitini kontrol et
        if len(self.conversation_history[user_id]) > self.max_history * 2:
            self.conversation_history[user_id] = self.conversation_history[user_id][-(self.max_history * 2):]
        self.last_activity[user_id] = time.time()
        
        # "Sen kimsin" gibi sorulara özel cevap (çok spesifik, false positive önlemi)
        kimsin_pattern = r'(\bsen\s+kim(sin)?\b|\bkim\s+olduğun\b|\bsen\s+nesin\b|\bnesin\s+sen\b|\bkendin(i)?\s+(tanıt|anlat)\b|\bbot\s+mu(sun)?\b|\bsen\s+bir?\s+bot\b)'
        if re.search(kimsin_pattern, question, re.IGNORECASE):
            intro = f"Ben @aizen'in AI botuyum! 🤖 Sohbet ederiz, !yardım yaz 😊"
            self.add_to_history(user_id, "assistant", intro)
            self.bot.send(f"@{user_name} {intro}")
            return
        
        # Sohbet konusu açma isteği kontrolü
        if self.detect_topic_request(question):
            # İlgi çekici rastgele konu seç
            topic = self.get_random_topic()
            
            # Konuyu paylaş
            self.add_to_history(user_id, "assistant", topic)
            self.bot.send(f"@{user_name} {topic}")
            
            print(f"🗨️ [{user_name}] Sohbet konusu açıldı: {topic[:50]}...")
            return
        
        # API çağıran özellikler için rate limit kontrolü (spam önlemi)
        if not self.check_rate_limit(user_id):
            self.bot.send(f"@{user_name} ⏰ Yavaşla! Dakikada max {self.max_requests_per_minute} istek.")
            print(f"⚠️ [{user_name}] Rate limit aşıldı!")
            return
        
        # Döviz kuru sorusu kontrolü
        if self.detect_currency_question(question):
            print(f"💱 [{user_name}] Döviz kuru soruldu")
            
            try:
                currency_info = self._run_async(self.get_exchange_rates(), timeout=7)
                
                if currency_info:
                    formatted = self.format_currency_info(currency_info)
                    self.add_to_history(user_id, "assistant", formatted)
                    self.bot.send(f"@{user_name}\n{formatted}")
                    print(f"✅ [{user_name}] Döviz kurları gönderildi")
                else:
                    self.bot.send(f"@{user_name} Döviz verileri alınamadı 😕")
                    print(f"⚠️ [{user_name}] Döviz verileri alınamadı")
            except Exception as e:
                print(f"⚠️ [{user_name}] Döviz hatası: {e}")
                self.bot.send(f"@{user_name} Döviz verisi alırken hata oluştu 😕")
            
            return
        
        # Kripto fiyat sorusu kontrolü
        if self.detect_crypto_question(question):
            print(f"₿ [{user_name}] Kripto fiyatı soruldu")
            
            try:
                crypto_info = self._run_async(self.get_crypto_prices(), timeout=7)
                
                if crypto_info:
                    formatted = self.format_crypto_info(crypto_info)
                    self.add_to_history(user_id, "assistant", formatted)
                    self.bot.send(f"@{user_name}\n{formatted}")
                    print(f"✅ [{user_name}] Kripto fiyatları gönderildi")
                else:
                    self.bot.send(f"@{user_name} Kripto verileri alınamadı 😕")
                    print(f"⚠️ [{user_name}] Kripto verileri alınamadı")
            except Exception as e:
                print(f"⚠️ [{user_name}] Kripto hatası: {e}")
                self.bot.send(f"@{user_name} Kripto verisi alırken hata oluştu 😕")
            
            return
        
        # Kitap bilgisi kontrolü
        if self.detect_book_search(question):
            # Sorguyu temizle - "kitap", "oku" gibi kelimeleri çıkar
            search_query = question.lower()
            remove_words = ['kitap', 'book', 'yazar', 'oku', 'okuma', 'roman', 'hikaye', 'nedir', 'ne', 'hakkında', 'bilgi', 'ver', 'anlat']
            for word in remove_words:
                search_query = search_query.replace(word, ' ')
            search_query = ' '.join(search_query.split()).strip()
            
            if not search_query or len(search_query) < 2:
                self.bot.send(f"@{user_name} Hangi kitabı arıyorsun? 📚")
                return
            
            print(f"📚 [{user_name}] Kitap aranıyor: '{search_query}'")
            
            try:
                books = self._run_async(self.search_book(search_query), timeout=10)
                
                if books:
                    formatted, url = self.format_book_results(books)
                    message = f"@{user_name}\n{formatted}"
                    
                    if url:
                        self.bot.send_url(message, url)
                    else:
                        self.bot.send(message)
                    
                    print(f"✅ [{user_name}] Kitap bilgisi gönderildi: {search_query}")
                else:
                    self.bot.send(f"@{user_name} '{search_query}' kitabı bulunamadı 🔍")
                    print(f"⚠️ [{user_name}] Kitap bulunamadı: '{search_query}'")
            except Exception as e:
                print(f"⚠️ [{user_name}] Kitap arama hatası: {e}")
                self.bot.send(f"@{user_name} Kitap bilgisi alırken hata oluştu 😕")
            
            return
        
        # Oyun bilgisi kontrolü
        if self.detect_game_search(question):
            # Sorguyu temizle - "oyun", "hakkında" gibi kelimeleri çıkar
            search_query = question.lower()
            remove_words = ['oyun', 'game', 'hakkında', 'bilgi', 'ver', 'anlat', 'nedir', 'ne', 'oyna', 'play', 'indir']
            for word in remove_words:
                search_query = search_query.replace(word, ' ')
            search_query = ' '.join(search_query.split()).strip()
            
            if not search_query or len(search_query) < 2:
                self.bot.send(f"@{user_name} Hangi oyunu arıyorsun? 🎮")
                return
            
            print(f"🎮 [{user_name}] Oyun aranıyor: '{search_query}'")
            
            try:
                game_info = self._run_async(self.search_game(search_query), timeout=10)
                
                if game_info:
                    formatted, url = self.format_game_results(game_info)
                    message = f"@{user_name}\n{formatted}"
                    
                    if url:
                        self.bot.send_url(message, url)
                    else:
                        self.bot.send(message)
                    
                    print(f"✅ [{user_name}] Oyun bilgisi gönderildi: {search_query}")
                else:
                    self.bot.send(f"@{user_name} '{search_query}' oyunu bulunamadı 🔍")
                    print(f"⚠️ [{user_name}] Oyun bulunamadı: '{search_query}'")
            except Exception as e:
                print(f"⚠️ [{user_name}] Oyun arama hatası: {e}")
                self.bot.send(f"@{user_name} Oyun bilgisi alırken hata oluştu 😕")
            
            return
        
        # Müzik arama kontrolü
        if self.detect_music_search(question):
            # Sorguyu temizle - "şarkısı", "müzik" gibi kelimeleri çıkar
            search_query = question.lower()
            remove_words = ['şarkı', 'şarkısı', 'müzik', 'music', 'song', 'dinle', 'parça', 'track', 'nedir', 'ne', 'kim', 'söylüyor']
            for word in remove_words:
                search_query = search_query.replace(word, ' ')
            search_query = ' '.join(search_query.split()).strip()
            
            if not search_query:
                self.bot.send(f"@{user_name} Hangi şarkıyı arıyorsun? 🎵")
                return
            
            print(f"🎵 [{user_name}] Müzik aranıyor: '{search_query}'")
            
            try:
                music_list = self._run_async(self.search_music(search_query, 5), timeout=10)
                
                if music_list:
                    formatted, url = self.format_music_results(music_list)
                    message = f"@{user_name}\n{formatted}"
                    
                    if url:
                        self.bot.send_url(message, url)
                    else:
                        self.bot.send(message)
                    
                    print(f"✅ [{user_name}] Müzik sonuçları gönderildi: {search_query}")
                else:
                    self.bot.send(f"@{user_name} '{search_query}' için müzik bulunamadı 🔍")
                    print(f"⚠️ [{user_name}] Müzik bulunamadı: '{search_query}'")
            except Exception as e:
                print(f"⚠️ [{user_name}] Müzik arama hatası: {e}")
                self.bot.send(f"@{user_name} Müzik ararken hata oluştu 😕")
            
            return
        
        # Wikipedia sorgusu kontrolü
        if self.detect_wikipedia_request(question):
            # Sorguyu temizle - "nedir", "kimdir" gibi kelimeleri çıkar
            search_query = question.lower()
            remove_words = ['nedir', 'kimdir', 'ne demek', 'ne anlama', 'açıkla', 'tanımı', 'tanım', 'vikipedi', 'wikipedia', 'gelir', 'geliyor']
            for word in remove_words:
                search_query = search_query.replace(word, ' ')
            search_query = ' '.join(search_query.split()).strip()
            
            print(f"📚 [{user_name}] Wikipedia sorgusu: '{search_query}'")
            
            try:
                wiki_info = self._run_async(self.search_wikipedia(search_query), timeout=7)
                
                if wiki_info:
                    formatted, url = self.format_wikipedia_summary(wiki_info)
                    message = f"@{user_name}\n{formatted}"
                    
                    if url:
                        self.bot.send_url(message, url)
                    else:
                        self.bot.send(message)
                    
                    print(f"✅ [{user_name}] Wikipedia özeti gönderildi: {wiki_info['title']} (URL: {url})")
                else:
                    self.bot.send(f"@{user_name} Wikipedia'da '{search_query}' bulunamadı 🔍")
                    print(f"⚠️ [{user_name}] Wikipedia'da bulunamadı: '{search_query}'")
            except Exception as e:
                print(f"⚠️ [{user_name}] Wikipedia hatası: {e}")
                self.bot.send(f"@{user_name} Wikipedia ararken hata oluştu 😕")
            
            return
        
        # Film önerisi isteği kontrolü
        if self.detect_movie_request(question):
            print(f"🎬 [{user_name}] Film önerisi istendi")
            
            try:
                movies = self._run_async(self.get_tmdb_popular_movies(5), timeout=7)
                
                if movies:
                    recommendation, url = self.format_movie_recommendation(movies)
                    message = f"@{user_name} İşte popüler filmler:\n{recommendation}"
                    self.add_to_history(user_id, "assistant", f"İşte popüler filmler:\n{recommendation}")
                    
                    if url:
                        self.bot.send_url(message, url)
                    else:
                        self.bot.send(message)
                    
                    print(f"✅ [{user_name}] Film önerileri gönderildi (URL: {url})")
                else:
                    self.bot.send(f"@{user_name} Film verisi alınamadı, TMDb API key kontrolü yap")
                    print(f"⚠️ [{user_name}] Film verisi alınamadı")
            except Exception as e:
                print(f"⚠️ [{user_name}] Film önerisi hatası: {e}")
                self.bot.send(f"@{user_name} Film önerisi alırken hata oluştu 😕")
            
            return
        
        # Dizi önerisi isteği kontrolü
        if self.detect_tv_request(question):
            print(f"📺 [{user_name}] Dizi önerisi istendi")
            
            try:
                shows = self._run_async(self.get_tmdb_popular_tv(5), timeout=7)
                
                if shows:
                    recommendation, url = self.format_tv_recommendation(shows)
                    message = f"@{user_name} İşte popüler diziler:\n{recommendation}"
                    
                    if url:
                        self.bot.send_url(message, url)
                    else:
                        self.bot.send(message)
                    
                    print(f"✅ [{user_name}] Dizi önerileri gönderildi (URL: {url})")
                else:
                    self.bot.send(f"@{user_name} Dizi verisi alınamadı, TMDb API key kontrolü yap")
                    print(f"⚠️ [{user_name}] Dizi verisi alınamadı")
            except Exception as e:
                print(f"⚠️ [{user_name}] Dizi önerisi hatası: {e}")
                self.bot.send(f"@{user_name} Dizi önerisi alırken hata oluştu 😕")
            
            return
        
        # Film arama (detaylı bilgi)
        if self.detect_movie_search(question):
            search_query = self.extract_search_query(question)
            print(f"🔍 [{user_name}] Film aranıyor: '{search_query}'")
            
            try:
                movie = self._run_async(self.search_tmdb_movie(search_query), timeout=7)
                
                if movie:
                    movie_id = movie.get('id')
                    # Detaylı bilgi çek
                    details = self._run_async(self.get_movie_details(movie_id), timeout=7)
                    
                    if details:
                        formatted, url = self.format_movie_details(details)
                        message = f"@{user_name}\n{formatted}"
                        
                        if url:
                            self.bot.send_url(message, url)
                        else:
                            self.bot.send(message)
                        
                        print(f"✅ [{user_name}] Film bilgisi gönderildi: {details['title']} (URL: {url})")
                    else:
                        self.bot.send(f"@{user_name} Film detayları alınamadı 😕")
                else:
                    self.bot.send(f"@{user_name} Bu film bulunamadı. Farklı bir isim dene 🔍")
                    print(f"⚠️ [{user_name}] Film bulunamadı: '{search_query}'")
            except Exception as e:
                print(f"⚠️ [{user_name}] Film arama hatası: {e}")
                self.bot.send(f"@{user_name} Film ararken hata oluştu 😕")
            
            return
        
        # Dizi arama (detaylı bilgi)
        if self.detect_tv_search(question):
            search_query = self.extract_search_query(question)
            print(f"🔍 [{user_name}] Dizi aranıyor: '{search_query}'")
            
            try:
                show = self._run_async(self.search_tmdb_tv(search_query), timeout=7)
                
                if show:
                    show_id = show.get('id')
                    # Detaylı bilgi çek
                    details = self._run_async(self.get_tv_details(show_id), timeout=7)
                    
                    if details:
                        formatted, url = self.format_tv_details(details)
                        message = f"@{user_name}\n{formatted}"
                        
                        if url:
                            self.bot.send_url(message, url)
                        else:
                            self.bot.send(message)
                        
                        print(f"✅ [{user_name}] Dizi bilgisi gönderildi: {details['title']} (URL: {url})")
                    else:
                        self.bot.send(f"@{user_name} Dizi detayları alınamadı 😕")
                else:
                    self.bot.send(f"@{user_name} Bu dizi bulunamadı. Farklı bir isim dene 🔍")
                    print(f"⚠️ [{user_name}] Dizi bulunamadı: '{search_query}'")
            except Exception as e:
                print(f"⚠️ [{user_name}] Dizi arama hatası: {e}")
                self.bot.send(f"@{user_name} Dizi ararken hata oluştu 😕")
            
            return
        
        # İstatistik güncelle
        self.stats['total_messages'] += 1
        self.stats['total_users'].add(user_id)
        self.stats['user_message_count'][user_id] += 1
        self.last_activity[user_id] = time.time()
        
        # Eski geçmişi temizle
        self.cleanup_old_history()
        
        # Hava durumu kontrolü
        weather_context = ""
        city = self.detect_city_in_question(question)
        if city:
            print(f"🌤️ [{user_name}] Hava durumu sorgusu tespit edildi: {city}")
            try:
                weather_data = self._run_async(self.get_weather_data(city), timeout=7)
                
                if weather_data:
                    weather_context = f"\n\n[HAVA DURUMU - {weather_data['city']}: {weather_data['temp_c']}°C, Hissedilen: {weather_data['feels_like']}°C, {weather_data['condition']}, Nem: %{weather_data['humidity']}, Rüzgar: {weather_data['wind_kph']} km/h]"
                    print(f"✅ [{user_name}] Hava durumu verisi alındı: {weather_data['city']}")
                else:
                    print(f"⚠️ [{user_name}] Hava durumu verisi alınamadı")
            except Exception as e:
                print(f"⚠️ [{user_name}] Hava durumu hatası: {e}")
        
        # Cevap üret (hava durumu context'i ile)
        response = self.get_ai_response(question, user_id, user_name, weather_context)
        
        # AI cevabındaki baştaki @username'i temizle (çift etiket önlemi)
        # AI bazen cevaba @Days, @aizen gibi ekliyor, biz de ekliyoruz → çift oluyor
        response = re.sub(rf'^@{re.escape(user_name)}[,:]?\s*', '', response, flags=re.IGNORECASE).strip()
        
        # Cevabı gönder ve kullanıcıyı etiketle
        self.bot.send(f"@{user_name} {response}")
        print(f"✅ [{user_name}] Cevap gönderildi: {response[:50]}...")
        
        # Bot cevabını da room_history'e ekle
        self.room_history.append({
            "user": "AI-zen",
            "message": f"@{user_name} {response}",
            "time": time.time()
        })
        if len(self.room_history) > self.max_room_history:
            self.room_history = self.room_history[-self.max_room_history:]
    
    def handle_dm(self, msg):
        """Direct mesajlara cevap verir"""
        if not self.ai_provider:
            self.bot.dm(msg.user.id, "⚠️ AI provider ayarlanmamış!")
            return
        
        question = msg.message.strip()
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user and msg.user.name else "misafir"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        
        # User name boş veya sadece whitespace ise
        if not user_name or not user_name.strip():
            user_name = "misafir"
        
        # Cevap üret
        response = self.get_ai_response(question, user_id, user_name)
        
        # Private mesaj olarak cevapla
        self.bot.dm(msg.user.id, response)
    
    # ==================== UNIFIED AI CALL ====================
    
    def _call_ai(self, messages, temperature=None, max_tokens=None):
        """Unified AI çağrısı - Gemini veya Groq kullanır.
        
        Args:
            messages: OpenAI formatında mesaj listesi [{"role": "system/user/assistant", "content": "..."}]
            temperature: Opsiyonel temperature override
            max_tokens: Opsiyonel max_tokens override
        
        Returns:
            str: AI'ın cevabı (stripped)
        
        Raises:
            Exception: AI provider ayarlı değilse veya API hatası olursa
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens
        
        if self.ai_provider == 'gemini':
            # Key rotasyonu ile Gemini rate limit yönetimi
            now = time.time()
            
            # Müsait bir key bul (tüm key'leri dene)
            for attempt in range(len(self.gemini_clients)):
                idx = (self.gemini_client_index + attempt) % len(self.gemini_clients)
                
                # Bu key'in son 60 saniyelik istek sayısını kontrol et
                self.gemini_key_timestamps[idx] = [
                    t for t in self.gemini_key_timestamps[idx] if now - t < 60
                ]
                
                if len(self.gemini_key_timestamps[idx]) < self.gemini_per_key_rpm:
                    # Bu key müsait!
                    self.gemini_client = self.gemini_clients[idx]
                    self.gemini_client_index = (idx + 1) % len(self.gemini_clients)  # Sonraki sefere sıradaki key
                    self.gemini_key_timestamps[idx].append(now)
                    
                    if attempt > 0:
                        print(f"🔄 Gemini key #{idx+1}'e geçildi (key rotasyonu)")
                    
                    return self._call_gemini(messages, temp, tokens)
            
            # Tüm key'ler doluysa: kısa bekle ve en az dolu key ile tekrar dene
            # (Groq'a düşmek yerine 3-5 sn bekleyip Gemini'den cevap almayı tercih et)
            min_idx = min(range(len(self.gemini_clients)), 
                         key=lambda i: len(self.gemini_key_timestamps[i]))
            min_count = len(self.gemini_key_timestamps[min_idx])
            
            # Eğer sadece 1-2 istek fazlaysa bekle, çok doluysa Groq'a geç
            if min_count <= self.gemini_per_key_rpm + 2:
                # En eski isteğin süresi dolana kadar bekle
                oldest = min(self.gemini_key_timestamps[min_idx])
                wait_time = 60 - (now - oldest) + 0.5  # +0.5 güvenlik payı
                if wait_time <= 8:  # Max 8 sn bekle
                    print(f"⏳ Gemini key'leri dolu, {wait_time:.1f}sn bekleniyor (key #{min_idx+1})...")
                    time.sleep(wait_time)
                    self.gemini_client = self.gemini_clients[min_idx]
                    self.gemini_key_timestamps[min_idx] = [
                        t for t in self.gemini_key_timestamps[min_idx] if time.time() - t < 60
                    ]
                    self.gemini_key_timestamps[min_idx].append(time.time())
                    return self._call_gemini(messages, temp, tokens)
            
            # Bekleme süresi çok uzunsa veya çok doluysa Groq fallback
            if self.groq_client:
                total_rpm = len(self.gemini_clients) * self.gemini_per_key_rpm
                print(f"⚠️ Tüm Gemini key'leri dolu ({total_rpm}/dk) → Groq fallback")
                return self._call_groq(messages, temp, min(tokens, 300))
            # Groq da yoksa en az dolu key ile zorla dene
            self.gemini_client = self.gemini_clients[min_idx]
            return self._call_gemini(messages, temp, tokens)
        elif self.ai_provider == 'groq':
            return self._call_groq(messages, temp, tokens)
        else:
            raise Exception("AI provider ayarlanmamış! GEMINI_API_KEY veya GROQ_API_KEY gerekli.")
    
    def _call_gemini(self, messages, temperature, max_tokens):
        """Google Gemini API çağrısı (yeni google-genai SDK)
        Rate limit'e takılırsa otomatik retry yapar, başarısız olursa Groq'a fallback."""
        # OpenAI formatındaki mesajları Gemini formatına çevir
        gemini_contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                system_instruction = content
                continue
            elif role == 'assistant':
                gemini_contents.append(
                    genai_types.Content(role="model", parts=[genai_types.Part(text=content)])
                )
            elif role == 'user':
                gemini_contents.append(
                    genai_types.Content(role="user", parts=[genai_types.Part(text=content)])
                )
        
        # Gemini API çağrısı
        try:
            response = self.gemini_client.models.generate_content(
                model=self.model,
                contents=gemini_contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_instruction or self.system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    thinking_config=genai_types.ThinkingConfig(
                        thinking_budget=256  # Düşünmeye az token, cevaba çok token
                    ),
                ),
            )
            
            # Gemini safety filter kontrolü
            if not response.text:
                # Detaylı hata bilgisi
                if response.candidates:
                    candidate = response.candidates[0]
                    finish = getattr(candidate, 'finish_reason', 'UNKNOWN')
                    print(f"⚠️ Gemini boş yanıt - finish_reason: {finish}")
                raise Exception("Gemini içerik üretemedi (safety filter veya boş yanıt)")
            
            # Finish reason kontrolü - truncation tespiti
            if response.candidates:
                candidate = response.candidates[0]
                finish = getattr(candidate, 'finish_reason', None)
                if finish and str(finish) not in ('STOP', 'FinishReason.STOP', 'None'):
                    print(f"⚠️ Gemini finish_reason: {finish} (yanıt kesilmiş olabilir)")
            
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Rate limit hatası - başka key dene, bekle, sonra Groq'a geç
            if 'resource_exhausted' in error_str or '429' in error_str or 'quota' in error_str:
                # Bu key'i "dolu" olarak işaretle (lokal tracking'i Google ile senkronize et)
                current_idx = self.gemini_clients.index(self.gemini_client) if self.gemini_client in self.gemini_clients else -1
                if current_idx >= 0:
                    now = time.time()
                    # Bu key'e yeterli timestamp ekle ki 60 sn boyunca tekrar seçilmesin
                    self.gemini_key_timestamps[current_idx] = [now] * (self.gemini_per_key_rpm + 1)
                
                # Başka Gemini key var mı?
                for attempt in range(1, len(self.gemini_clients)):
                    next_idx = (current_idx + attempt) % len(self.gemini_clients)
                    now = time.time()
                    self.gemini_key_timestamps[next_idx] = [
                        t for t in self.gemini_key_timestamps[next_idx] if now - t < 60
                    ]
                    if len(self.gemini_key_timestamps[next_idx]) < self.gemini_per_key_rpm:
                        print(f"🔄 Gemini key #{current_idx+1} rate limit → key #{next_idx+1}'e geçiliyor")
                        self.gemini_client = self.gemini_clients[next_idx]
                        self.gemini_key_timestamps[next_idx].append(now)
                        time.sleep(0.5)  # Key'ler arası kısa bekleme
                        return self._call_gemini(messages, temperature, max_tokens)
                
                # Tüm key'ler doluysa: Groq'a düşmeden önce 10 sn bekleyip son bir kez dene
                print("⏳ Tüm Gemini key'leri dolu, 10sn bekleniyor (son deneme)...")
                time.sleep(10)
                
                # Bekleme sonrası en az dolu key'i bul
                best_idx = min(range(len(self.gemini_clients)),
                               key=lambda i: len([t for t in self.gemini_key_timestamps[i] if time.time() - t < 60]))
                fresh_count = len([t for t in self.gemini_key_timestamps[best_idx] if time.time() - t < 60])
                
                if fresh_count < self.gemini_per_key_rpm:
                    print(f"✅ Bekleme sonrası key #{best_idx+1} müsait, tekrar deneniyor...")
                    self.gemini_client = self.gemini_clients[best_idx]
                    self.gemini_key_timestamps[best_idx].append(time.time())
                    try:
                        return self._call_gemini(messages, temperature, max_tokens)
                    except Exception:
                        pass  # Son deneme de başarısızsa Groq'a geç
                
                # Groq fallback
                if self.groq_client:
                    print("🔄 Tüm Gemini key'leri rate limit → Groq fallback kullanılıyor...")
                    return self._call_groq(messages, temperature, min(max_tokens, 300))
                else:
                    raise Exception("Gemini rate limit aşıldı ve Groq fallback yok. Biraz bekleyin.")
            else:
                # Safety, network vs. hatalar - Groq fallback dene
                if self.groq_client:
                    print(f"⚠️ Gemini hatası ({str(e)[:60]}) → Groq fallback...")
                    return self._call_groq(messages, temperature, min(max_tokens, 300))
                raise
    
    def _call_groq(self, messages, temperature, max_tokens):
        """Groq API çağrısı"""
        # Groq'ta en kaliteli bedava model
        groq_model = "llama-3.3-70b-versatile"
        completion = self.groq_client.chat.completions.create(
            model=groq_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content.strip()
    
    # ==================== UNIFIED AI CALL BİTİŞ ====================
    
    def get_ai_response(self, question, user_id, user_name, weather_context=""):
        """AI ile cevap üretir (Gemini veya Groq)"""
        try:
            # Güncel tarih ve saat bilgisini al (Türkiye saati)
            dt = self.get_turkish_datetime()
            
            # Context bilgisi (tarih/saat + hava durumu)
            time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {dt['time_str']}, Tarih: {dt['date_str']} {dt['day_name']}]"
            if weather_context:
                time_context += weather_context
            
            # Kullanıcı için conversation history oluştur (mesaj zaten handle_mention'da eklendi)
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # History'de son mesaj zaten bu soru mu kontrol et (duplicate önlemi)
            if not self.conversation_history[user_id] or self.conversation_history[user_id][-1].get('content') != question:
                self.conversation_history[user_id].append({
                    "role": "user",
                    "content": question
                })
            
            # History çok uzunsa eski mesajları sil (system prompt hariç)
            if len(self.conversation_history[user_id]) > self.max_history * 2:
                self.conversation_history[user_id] = self.conversation_history[user_id][-(self.max_history * 2):]
            
            # AI API çağrısı (Gemini veya Groq)
            # Son mesaja user_name + time_context ekle (history'ye değil, sadece API çağrısına)
            api_history = self.conversation_history[user_id].copy()
            if api_history:
                last_msg = api_history[-1].copy()
                last_msg["content"] = f"[Yazan: @{user_name}] {question}" + time_context
                api_history[-1] = last_msg
            
            # Oda sohbet geçmişini context olarak ekle (cross-user farkındalık)
            room_context = ""
            if self.room_history:
                # Son mesajları özetle (mevcut kullanıcının mesajları hariç - zaten history'de var)
                recent_room = [
                    f"@{m['user']}: {m['message'][:100]}"
                    for m in self.room_history[-15:]  # Son 15 mesaj
                    if m['user'] != user_name  # Kendi mesajlarını tekrar ekleme
                ]
                if recent_room:
                    room_context = "\n\n[ODA SOHBETİ - Son mesajlar (başka kullanıcılardan):\n" + "\n".join(recent_room) + "]"
            
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + api_history
            
            # Room context'i son user mesajına ekle
            if room_context and messages:
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i]["role"] == "user":
                        messages[i] = messages[i].copy()
                        messages[i]["content"] += room_context
                        break
            
            response = self._call_ai(messages)
            
            # Debug: AI'ın ürettiği cevabı göster
            print(f"🤖 [{self.ai_provider}] AI Response for {user_name}: '{response}'")
            
            # Cevap validasyonu (sadece loglama, fallback YOK)
            is_valid, reason = self.validate_response(response)
            
            if not is_valid:
                print(f"⚠️  VALIDATION WARNING: {reason} (ama yine de kullanılıyor)")
            
            # AI cevabını history'e ekle (validation başarısız olsa bile orijinal cevap kullanılır)
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ AI API hatası ({self.ai_provider}): {error_msg}")
            
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                return "⚠️ API key hatası. Lütfen kontrol edin."
            elif "rate_limit" in error_msg.lower():
                return "⚠️ Rate limit aşıldı. Biraz bekleyin ve tekrar deneyin."
            else:
                return f"⚠️ Üzgünüm, bir hata oluştu: {error_msg[:100]}"
    
    def handle_join(self, msg):
        """Kullanıcı odaya katıldığında çağrılır"""
        if not msg.user:
            return
        
        user_name = msg.user.name
        user_id = msg.user.id
        
        # User name kontrolü - None, boş veya sadece whitespace ise default kullan
        if not user_name or not user_name.strip():
            user_name = "misafir"
            print(f"⚠️  Kullanıcı adı boş geldi (ID: {user_id}), 'misafir' olarak ayarlandı")
        
        user_name_lower = user_name.lower()
        
        # Bot'un kendi user ID'sini al
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        
        # Bot kendine selam vermesin!
        if user_id == bot_user_id:
            # Bot'u known_users'a ekle ama selam verme
            self.known_users.add(user_id)
            return
        
        # Bu kullanıcı zaten odada mıydı? (JOIN spam önlemi)
        if user_id in self.known_users:
            # Zaten bilinen kullanıcı, selam verme
            return
        
        # Yeni kullanıcı! Known users'a ekle
        self.known_users.add(user_id)
        print(f"👋 Yeni kullanıcı katıldı: {user_name} (ID: {user_id})")
        
        # Odaya katılan kullanıcıyı selamla
        self.bot.send(f"@{user_name} Hoş geldin! 👋😊")
        
        # "aizen" kullanıcı adıyla gelen kullanıcılara şifre sor
        if user_name_lower == "aizen":
            if user_id not in self.authenticated_owners and user_id not in self.pending_password:
                self.pending_password[user_id] = user_name
                self.bot.dm(user_id, "🔐 Sen gerçek aizen misin? Şifreni söyle!")
                print(f"🔐 Şifre soruldu: {user_name}")
    
    def handle_leave(self, msg):
        """Kullanıcı odadan ayrıldığında çağrılır"""
        if not msg.user:
            return
        
        user_id = msg.user.id
        user_name = msg.user.name if msg.user.name and msg.user.name.strip() else "misafir"
        
        # Known users'dan çıkar (tekrar katıldığında selamlansın)
        if user_id in self.known_users:
            self.known_users.remove(user_id)
            print(f"👋 Kullanıcı ayrıldı: {user_name} (ID: {user_id})")
        
        # Kullanıcı ayrılıyorsa authenticated listeden çıkar
        if user_id in self.authenticated_owners:
            self.authenticated_owners.remove(user_id)
            print(f"👋 Owner ayrıldı: {user_name} (ID: {user_id})")
        
        # Pending password listesinden de çıkar
        if user_id in self.pending_password:
            del self.pending_password[user_id]
    
    def check_existing_aizen_users(self):
        """Odada zaten var olan 'aizen' kullanıcılarını ve aileyi kontrol eder"""
        if not self.bot.room or not self.bot.room.users:
            return
        
        # Bot'un kendi user ID'sini al
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        
        # Odadaki tüm kullanıcıları kontrol et
        for user_id, user in self.bot.room.users.items():
            if user and hasattr(user, 'name') and user.name:
                # Tüm mevcut kullanıcıları known_users'a ekle (JOIN spamı önlemek için)
                self.known_users.add(user_id)
                
                # Bot kendine şifre sormamalı!
                if user_id == bot_user_id:
                    continue
                
                if user.name.lower() == "aizen":
                    # Bu kullanıcıya daha önce şifre sorulmadıysa ve doğrulanmadıysa sor
                    if user_id not in self.pending_password and user_id not in self.authenticated_owners:
                        self.pending_password[user_id] = user.name
                        self.bot.dm(user_id, "🔐 Sen gerçek aizen misin? Şifreni söyle!")
                        print(f"🔐 Şifre soruldu: {user.name}")
    
    def handle_dm_password(self, msg):
        """DM'lerde şifre kontrolü ve özel kullanıcılar için AI cevabı"""
        if not msg.user:
            return
        
        user_id = msg.user.id
        user_name = msg.user.name if msg.user.name and msg.user.name.strip() else "misafir"
        user_name_lower = user_name.lower()
        
        # ÖNCE şifre kontrolü (aizen owner authentication)
        if user_id in self.pending_password:
            password_attempt = msg.message.strip()
            
            if password_attempt == self.owner_password:
                # Doğru şifre!
                self.bot.dm(user_id, "✅ Hoş geldin baba! 👑")
                # Herkese görünsün
                self.bot.send(f"✅ Hoş geldin @{user_name} baba! 👑🎉")
                self.authenticated_owners.add(user_id)  # Doğrulanmış listeye ekle
                del self.pending_password[user_id]
                print(f"✅ Owner doğrulandı: {user_name} (ID: {user_id})")
            else:
                # Yanlış şifre!
                self.bot.dm(user_id, "❌ Sen babam değilsin, dolandırıcı! 🚫")
                # Herkese görünsün
                self.bot.send(f"🚨 @{user_name} SEN GERÇEK AIZEN DEĞİLSİN PİÇ KURUSU! 🚨")
                del self.pending_password[user_id]
                print(f"⚠️  Yanlış şifre: {user_name}")
            return
        
        # Özel kullanıcılar: aizen (baba), pepejulianonzima (anne), ghost - bunlara AI ile cevap ver
        special_users = ['aizen', 'pepejulianonzima', 'ghost']
        
        if user_name_lower in special_users:
            # Bu özel kullanıcılardan birine AI ile cevap ver
            if not self.ai_provider:
                self.bot.dm(user_id, "⚠️ AI provider ayarlanmamış!")
                return
            
            question = msg.message.strip()
            
            if not question:
                return
            
            print(f"💬 DM [{user_name}]: {question[:50]}...")
            
            # Rate limit kontrolü
            if not self.check_rate_limit(user_id):
                self.bot.dm(user_id, "⏳ Çok hızlı mesaj atıyorsun! Biraz bekle 😊")
                return
            
            # İstatistik güncelle (DM'ler de sayılsın)
            self.stats['total_messages'] += 1
            self.stats['total_users'].add(user_id)
            self.stats['user_message_count'][user_id] += 1
            
            # Eski geçmişi temizle
            self.cleanup_old_history()
            
            # Kullanıcı geçmişini al veya oluştur
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            history = self.conversation_history[user_id]
            
            # Kullanıcının son aktivite zamanını güncelle
            self.last_activity[user_id] = time.time()
            
            # Gerçek zamanlı bağlam ekle
            dt = self.get_turkish_datetime()
            
            time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {dt['time_str']}, Tarih: {dt['date_str']} {dt['day_name']}]"
            question_with_context = question + time_context
            
            # AI API'ye istek gönder
            try:
                messages = [
                    {"role": "system", "content": self.system_prompt}
                ]
                
                # Geçmiş konuşmaları ekle
                messages.extend(history)
                
                # Güncel soruyu ekle
                messages.append({"role": "user", "content": question_with_context})
                
                answer = self._call_ai(messages)
                
                # Debug: AI'ın ürettiği cevabı göster
                print(f"🤖 DM AI Response for {user_name}: '{answer}'")
                
                # Cevap validasyonu (sadece loglama, fallback YOK)
                is_valid, reason = self.validate_response(answer)
                
                if not is_valid:
                    print(f"⚠️  DM VALIDATION WARNING: {reason} (ama yine de kullanılıyor)")
                
                # Geçmişe ekle (get_ai_response ile aynı dict formatı - context OLMADAN, token tasarrufu)
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": answer})
                if len(history) > self.max_history * 2:
                    history[:] = history[-(self.max_history * 2):]
                
                # DM ile cevap ver
                self.bot.dm(user_id, answer)
                print(f"✅ DM [{user_name}]: Cevap gönderildi")
                
            except Exception as e:
                print(f"⚠️ DM AI hatası [{user_name}]: {e}")
                error_msg = "⚠️ Cevap verirken hata oluştu 😕"
                
                if "api_key" in str(e).lower():
                    error_msg = "⚠️ API key hatası. Lütfen kontrol edin."
                elif "rate_limit" in str(e).lower():
                    error_msg = "⚠️ Rate limit aşıldı. Biraz bekleyin."
                
                self.bot.dm(user_id, error_msg)
            
            return
        
        # Diğer kullanıcıların DM'leri ignore edilir (sadece özel kullanıcılar cevap alır)
    
    # ==================== YENİ KOMUTLAR ====================
    
    def help_cmd(self, msg):
        """Yardım komutu"""
        help_text = """📖 AI-zen Komutları

@AI-zen [mesaj] → Sohbet/Bilgi/Hava/Film
!saat !hesap !çevir !haber !isim
!döviz !kripto !müzik !kitap !oyun
!şaka !fal !zar !yazıtura !şans
!rastgele !tahmin !burç !atasözü
!unutbeni → Geçmişi sil
👑 !stats !model !temp !clear"""
        self.bot.send(help_text)
    
    def time_cmd(self, msg):
        """Saat komutu"""
        dt = self.get_turkish_datetime()
        self.bot.send(f"🕐 Saat: {dt['time_str']} | 📅 {dt['date_str']} {dt['day_name']}")
    
    def forget_me(self, msg):
        """Kullanıcının kendi geçmişini silmesini sağlar"""
        user_id = msg.user.id if msg.user else None
        user_name = msg.user.name if msg.user and msg.user.name and msg.user.name.strip() else "misafir"
        
        if user_id and user_id in self.conversation_history and len(self.conversation_history[user_id]) > 0:
            del self.conversation_history[user_id]
            self.bot.send(f"@{user_name} 🗑️ Konuşma geçmişin silindi!")
        else:
            self.bot.send(f"@{user_name} Zaten kayıtlı bir geçmişin yok.")
    
    def stats_cmd(self, msg):
        """İstatistikler (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        uptime = int(time.time() - self.stats['start_time'])
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days}g "
        uptime_str += f"{hours}s {minutes}d"
        
        active_convos = len(self.conversation_history)
        active_games = len(self.guess_game_sessions)
        
        stats_text = f"""📊 Bot İstatistikleri:
✅ Toplam mesaj: {self.stats['total_messages']}
👥 Toplam kullanıcı: {len(self.stats['total_users'])}
⏰ Uptime: {uptime_str}
� Provider: {self.ai_provider or 'Yok'}
�🤖 Model: {self.model}
🌡️ Temp: {self.temperature}
💬 Aktif sohbet: {active_convos}
🎮 Aktif oyun: {active_games}"""
        self.bot.send(stats_text)
    
    def clear_cmd(self, msg):
        """Bir kullanıcının geçmişini temizle (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        target_name = msg.groups[0] if msg.groups else None
        if target_name:
            target_name_lower = target_name.lower().strip()
            # Odadaki kullanıcılardan isimle eşleştir
            found = False
            if self.bot.room and self.bot.room.users:
                for uid, user in self.bot.room.users.items():
                    if user and hasattr(user, 'name') and user.name and user.name.lower() == target_name_lower:
                        if uid in self.conversation_history:
                            del self.conversation_history[uid]
                            self.bot.send(f"🗑️ @{user.name} kullanıcısının sohbet geçmişi silindi!")
                        else:
                            self.bot.send(f"@{user.name} için kayıtlı geçmiş yok.")
                        found = True
                        break
            if not found:
                self.bot.send(f"❌ '{target_name}' kullanıcısı odada bulunamadı.")
        else:
            # Argümansız: tüm geçmişleri temizle
            count = len(self.conversation_history)
            self.conversation_history.clear()
            self.bot.send(f"🗑️ Tüm sohbet geçmişi temizlendi! ({count} kullanıcı)")
    
    def model_cmd(self, msg):
        """AI modelini değiştir (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        new_model = msg.groups[0] if msg.groups else None
        if new_model:
            # Provider değiştirme desteği
            if new_model.startswith('gemini'):
                if not GEMINI_AVAILABLE or not os.getenv('GEMINI_API_KEY'):
                    self.bot.send("⚠️ Gemini kullanmak için GEMINI_API_KEY gerekli!")
                    return
                if not self.gemini_client:
                    self.gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
                self.ai_provider = 'gemini'
            elif new_model.startswith('llama') or new_model.startswith('mixtral') or new_model.startswith('deepseek') or new_model.startswith('qwen'):
                if not os.getenv('GROQ_API_KEY'):
                    self.bot.send("⚠️ Groq kullanmak için GROQ_API_KEY gerekli!")
                    return
                if not self.groq_client:
                    self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                self.ai_provider = 'groq'
            
            old_model = self.model
            self.model = new_model
            self.bot.send(f"🤖 Model değiştirildi: {old_model} → {new_model} (Provider: {self.ai_provider})")
        else:
            self.bot.send(f"🧠 Provider: {self.ai_provider}\n🤖 Model: {self.model}\nKullanım: !model [model_adı]\nGemini: gemini-2.0-flash (1500/gün), gemini-2.5-flash (20/gün)\nGroq: llama-3.3-70b-versatile")
    
    def temp_cmd(self, msg):
        """Temperature ayarla (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        temp_str = msg.groups[0] if msg.groups else None
        if temp_str:
            try:
                new_temp = float(temp_str)
                if 0.0 <= new_temp <= 2.0:
                    old_temp = self.temperature
                    self.temperature = new_temp
                    self.bot.send(f"🌡️ Temperature: {old_temp} → {new_temp}")
                else:
                    self.bot.send("Temperature 0.0-2.0 arası olmalı!")
            except ValueError:
                self.bot.send("Geçersiz değer!")
        else:
            self.bot.send(f"🌡️ Mevcut temperature: {self.temperature}\nKullanım: !temp [0.0-2.0]")
    
    # ==================== YARDIMCI FONKSİYONLAR ====================
    
    def check_rate_limit(self, user_id):
        """Rate limit kontrolü"""
        now = time.time()
        
        # Eski istekleri temizle (60 saniyeden eski)
        self.rate_limit_tracker[user_id] = [
            timestamp for timestamp in self.rate_limit_tracker[user_id]
            if now - timestamp < 60
        ]
        
        # Limit kontrolü
        if len(self.rate_limit_tracker[user_id]) >= self.max_requests_per_minute:
            return False
        
        # Yeni isteği kaydet
        self.rate_limit_tracker[user_id].append(now)
        return True
    
    def cleanup_old_history(self):
        """1 saatten uzun süredir aktif olmayan kullanıcıların geçmişini temizle"""
        now = time.time()
        to_remove = []
        
        for user_id, last_time in self.last_activity.items():
            if now - last_time > self.inactivity_timeout:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            if user_id in self.conversation_history:
                del self.conversation_history[user_id]
            del self.last_activity[user_id]
    
    def add_to_history(self, user_id, role, content):
        """Conversation history'e mesaj ekler (özel komutların cevapları için)"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({
            "role": role,
            "content": content
        })
        # Limit kontrolü
        if len(self.conversation_history[user_id]) > self.max_history * 2:
            self.conversation_history[user_id] = self.conversation_history[user_id][-(self.max_history * 2):]
    
    def validate_response(self, response):
        """AI cevabını validate et - minimal kontrol, tam performans"""
        # Sadece boş/çok kısa cevapları engelle
        text_only = ''.join(c for c in response if c.isalnum() or c.isspace())
        if len(text_only.strip()) < 2:
            return False, f"Empty response ({len(response)} chars)"
        
        return True, "OK"
    
    def clear_history(self, user_id):
        """Belirli bir kullanıcının conversation history'sini temizler"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            print(f"🗑️  Cleared history for user: {user_id}")
    
    # ==================== EĞLENCE MODÜLÜ - KOMUTLAR ====================
    
    def joke_cmd(self, msg):
        """Rastgele Türkçe şaka anlat"""
        joke = random.choice(self.jokes)
        self.bot.send(f"😄 {joke}")
    
    def fortune_cmd(self, msg):
        """Eğlenceli günlük fal (kişi başı günde bir)"""
        user_id = msg.user.id if msg.user else "unknown"
        user_name = msg.user.name if msg.user else "??"
        
        # Her kullanıcı günde aynı falı alır (deterministik)
        dt = self.get_turkish_datetime()
        seed_str = f"fal_{user_id}_{dt['date_key']}"
        rng = random.Random(seed_str)
        fortune = rng.choice(self.fortunes)
        self.bot.send(f"@{user_name} {fortune}")
    
    def dice_cmd(self, msg):
        """Zar at (1-6), opsiyonel birden fazla zar: !zar 3"""
        groups = msg.groups
        count_str = groups[0] if groups[0] else groups[1] if groups[1] else groups[2] if groups[2] else None
        
        count = 1
        if count_str:
            try:
                count = int(count_str)
                count = max(1, min(count, 6))  # 1-6 arası zar
            except ValueError:
                count = 1
        
        dice_emojis = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
        
        if count == 1:
            result = random.randint(1, 6)
            self.bot.send(f"🎲 Zar atıldı: {dice_emojis[result - 1]} {result}")
        else:
            results = [random.randint(1, 6) for _ in range(count)]
            emoji_str = " ".join(dice_emojis[r - 1] for r in results)
            total = sum(results)
            self.bot.send(f"🎲 {count} zar atıldı: {emoji_str}\n📊 Toplam: {total}")
    
    def random_cmd(self, msg):
        """Rastgele sayı üret (min-max arası)"""
        groups = msg.groups
        
        # İki farklı format: !rastgele ya da !random
        if groups[0] and groups[1]:  # !rastgele format
            min_val = int(groups[0])
            max_val = int(groups[1])
        elif groups[2] and groups[3]:  # !random format
            min_val = int(groups[2])
            max_val = int(groups[3])
        else:
            self.bot.send("Kullanım: !rastgele [min] [max] veya !random [min] [max]")
            return
        
        if min_val > max_val:
            self.bot.send("❌ Minimum değer maksimumdan büyük olamaz!")
            return
        
        if max_val - min_val > 1000000:
            self.bot.send("❌ Aralık çok büyük (max 1 milyon)!")
            return
        
        result = random.randint(min_val, max_val)
        self.bot.send(f"🔢 Rastgele sayı ({min_val}-{max_val}): {result}")
    
    def luck_cmd(self, msg):
        """Bugünün şans skoru (1-100)"""
        user_id = msg.user.id if msg.user else "unknown"
        user_name = msg.user.name if msg.user else "??"
        
        # Kullanıcı ID + bugünün tarihi ile seed oluştur (Türkiye saati)
        dt = self.get_turkish_datetime()
        seed_str = f"{user_id}_{dt['date_key']}"
        
        # Seed'den deterministik sayı üret (thread-safe: ayrı Random instance)
        rng = random.Random(seed_str)
        luck_score = rng.randint(1, 100)
        
        # Emoji seç
        if luck_score >= 90:
            emoji = "🌟"
            comment = "Mükemmel!"
        elif luck_score >= 70:
            emoji = "✨"
            comment = "Çok iyi!"
        elif luck_score >= 50:
            emoji = "🍀"
            comment = "İyi!"
        elif luck_score >= 30:
            emoji = "😐"
            comment = "Fena değil."
        else:
            emoji = "😔"
            comment = "Kötü..."
        
        self.bot.send(f"{emoji} @{user_name} bugünün şans skoru: {luck_score}/100 - {comment}")
    
    def coinflip_cmd(self, msg):
        """Yazı tura at"""
        result = random.choice(['Yazı', 'Tura'])
        emoji = '🪙' if result == 'Yazı' else '🎯'
        self.bot.send(f"{emoji} Para atıldı: {result}!")
    
    # ==================== BURÇ YORUMLARI SİSTEMİ ====================
    
    def horoscope_cmd(self, msg):
        """Burç yorumu ver"""
        groups = msg.groups
        burc_name = groups[0] if groups[0] else groups[1] if groups[1] else groups[2] if groups[2] else None
        
        if not burc_name or not burc_name.strip():
            burc_list = "♈ Koç, ♉ Boğa, ♊ İkizler, ♋ Yengeç, ♌ Aslan, ♍ Başak, ♎ Terazi, ♏ Akrep, ♐ Yay, ♑ Oğlak, ♒ Kova, ♓ Balık"
            self.bot.send(f"🔮 Kullanım: !burç [burç adı]\n{burc_list}")
            return
        
        burc_name = burc_name.strip().lower()
        
        # Burç mapping
        burc_mapping = {
            'koç': ('♈', 'Koç'),
            'koc': ('♈', 'Koç'),
            'boğa': ('♉', 'Boğa'),
            'boga': ('♉', 'Boğa'),
            'ikizler': ('♊', 'İkizler'),
            'yengeç': ('♋', 'Yengeç'),
            'yengec': ('♋', 'Yengeç'),
            'aslan': ('♌', 'Aslan'),
            'başak': ('♍', 'Başak'),
            'basak': ('♍', 'Başak'),
            'terazi': ('♎', 'Terazi'),
            'akrep': ('♏', 'Akrep'),
            'yay': ('♐', 'Yay'),
            'oğlak': ('♑', 'Oğlak'),
            'oglak': ('♑', 'Oğlak'),
            'kova': ('♒', 'Kova'),
            'balık': ('♓', 'Balık'),
            'balik': ('♓', 'Balık')
        }
        
        if burc_name not in burc_mapping:
            self.bot.send(f"🔮 Bilinmeyen burç: {burc_name}\nÖrnek: !burç koç")
            return
        
        emoji, display_name = burc_mapping[burc_name]
        
        # Günlük deterministic yorum (her gün aynı burç için aynı yorum)
        dt = self.get_turkish_datetime()
        # hash() Python oturumları arasında değişir, stabil seed kullan
        burc_offset = sum(ord(c) for c in display_name)
        seed_str = f"burc_{display_name}_{dt['date_key']}_{burc_offset}"
        rng = random.Random(seed_str)
        
        # Burç yorumları koleksiyonu
        horoscope_texts = [
            "Bugün enerjiniz çok yüksek! Yeni işlere başlamak için ideal bir gün.",
            "Sevdiğiniz biri sizi düşünüyor olabilir. Mesajlarınızı kontrol edin!",
            "Bugün dikkatli olun, küçük hatalar büyük sorunlara yol açabilir.",
            "Finansal konularda şanslı bir gün! Yatırım yapmayı düşünebilirsiniz.",
            "Bugün kendinize zaman ayırın. Dinlenmek ve yenilenmeniz gerekiyor.",
            "Sosyal çevreniz genişleyecek. Yeni dostluklar kurabilirsiniz.",
            "Bugün iş hayatınızda önemli gelişmeler olabilir. Fırsatları kaçırmayın!",
            "Aşk hayatınızda sürprizler sizi bekliyor. Hazır olun!",
            "Bugün duygusal yönünüz ağır basacak. Empati kurmak kolay olacak.",
            "Planlı hareket etmeniz gereken bir gün. Aceleci davranmayın.",
            "Yaratıcılığınız zirve yapacak! Sanatsal işlerle uğraşmak için harika.",
            "Bugün ailevi konulara odaklanabilirsiniz. Yakınlarınızla vakit geçirin.",
            "Sağlığınıza dikkat edin. Düzenli beslenme ve spor önemli.",
            "Bugün şansınız yaver! Risk almaktan çekinmeyin.",
            "İletişim konusunda başarılı olacaksınız. Önemli konuşmalar yapın.",
            "Bugün sabırlı olmanız gerekecek. Aceleye gelmeyin.",
            "Mali durumunuzda iyileşme görülecek. Eski borçlar kapanabilir.",
            "Bugün içgüdülerinize güvenin. Sezgileriniz sizi yanıltmayacak.",
            "Yeni bir hobi edinmek için ideal bir gün. Kendinizi keşfedin!",
            "Bugün geçmişten biri ile karşılaşabilirsiniz. Hazırlıklı olun.",
            "İş teklifleri gelebilir. Değerlendirmeyi unutmayın.",
            "Bugün eğlenceye ve keyfe odaklanın. Stres atmak için zaman ayırın.",
            "Aile büyüklerinizden değerli tavsiyeler alabilirsiniz.",
            "Bugün teknoloji ve sosyal medyada aktif olmak size yarar sağlar.",
            "Romantik bir sürpriz yapabilir veya alabilirsiniz!",
            "Bugün öğrenmeye açık olun. Yeni bilgiler edineceksiniz.",
            "Kariyer hedeflerinize bir adım daha yaklaşacaksınız.",
            "Bugün duygusal anlamda güçlü hissedeceksiniz.",
            "Seyahat planları yapabilirsiniz. Uzak yerler sizi çağırıyor.",
            "Bugün çevrenize ilham vereceksiniz. Liderlik gösterin!"
        ]
        
        yorum = rng.choice(horoscope_texts)
        
        # Şans numarası (1-100)
        sans_num = rng.randint(1, 100)
        
        message = f"🔮 {emoji} {display_name} Burcu\n\n{yorum}\n\n🍀 Bugünün şans sayınız: {sans_num}"
        self.bot.send(message)
    
    # ==================== ATASÖZLER İ VE GÜZEL SÖZLER ====================
    
    def proverb_cmd(self, msg):
        """Rastgele atasözü veya güzel söz ver"""
        
        # Türkçe atasözleri koleksiyonu
        proverbs = [
            "Damlaya damlaya göl olur.",
            "Acele işe şeytan karışır.",
            "Ağaç yaşken eğilir.",
            "Ak akçe kara gün içindir.",
            "Ayağını yorganına göre uzat.",
            "Balık baştan kokar.",
            "Bir elin nesi var, iki elin sesi var.",
            "Bir fincan kahvenin kırk yıl hatırı vardır.",
            "Dost kara günde belli olur.",
            "El elin eşeğini türkü çağırarak arar.",
            "Güneş balçıkla sıvanmaz.",
            "Her şeyin başı sağlık.",
            "İşleyen demir pas tutmaz.",
            "Kaz gelen yerden tavuk esirgenmez.",
            "Komşu komşunun külüne muhtaçtır.",
            "Mart kapıdan baktırır, kazma kürek yaktırır.",
            "Mum dibinde karanlık olur.",
            "Para parayı çeker.",
            "Sakla samanı gelir zamanı.",
            "Yalancının mumu yatsıya kadar yanar."
        ]
        
        # Güzel sözler koleksiyonu
        quotes = [
            "Hayatta en hakiki mürşit ilimdir. - Mustafa Kemal Atatürk",
            "Bir kitap bir mektuptur. - Ahmet Hamdi Tanpınar",
            "Okumak bir ömür boyu süren harika bir serüvendir. - Füruzan",
            "Bilgi güçtür. - Francis Bacon",
            "Adalet mülkün temelidir. - Osmanlı Atasözü",
            "Eğitim hayatın kendisidir, hayata hazırlık değil. - John Dewey",
            "En büyük zenginlik sağlıktır. - Virgil",
            "Güzellik göz ile değil, kalp ile görülür. - Hz. Mevlana",
            "Hayat bisiklet gibidir. Dengeyi korumak için hareket etmelisin. - Albert Einstein",
            "İyilik yap denize at, balık bilmezse Halik bilir. - Yunus Emre",
            "Kitap okumayan bir toplum, sakat bir toplumdur. - Ahmet Ümit",
            "Mutluluk kapıdan bakan misafir gibidir. - Orhan Pamuk",
            "Sanat mutluluk verir, huzur verir. - Bedri Rahmi Eyüboğlu",
            "Sevgi insanın özüdür. - Nazım Hikmet",
            "Yol yoksa, açarız! - Fatih Sultan Mehmet",
            "Düşünen adam, kendi başına bir dünyadır. - Victor Hugo",
            "En iyi öğretmen, hatalarımızdır. - Anonim",
            "Geleceği inşa etmek için geçmişi bilmeliyiz. - Otto von Bismarck",
            "Hayal kurmak başarının ilk adımıdır. - Walt Disney",
            "İnsan sevdiği şey olur. - Hz. Mevlana"
        ]
        
        # Rastgele seç (atasözü veya güzel söz)
        all_items = proverbs + quotes
        selected = random.choice(all_items)
        
        emoji = "📜" if selected in proverbs else "💬"
        
        self.bot.send(f"{emoji} {selected}")
    
    # ==================== İLAVE OYUNLAR ====================
    
    def guess_number_cmd(self, msg):
        """Sayı tahmin oyunu (pes/iptal ile çıkılabilir)"""
        groups = msg.groups
        guess = groups[0] if groups[0] else groups[1] if groups[1] else groups[2] if groups[2] else groups[3] if groups[3] else None
        
        if not hasattr(msg, 'user') or not msg.user:
            return
        
        user_id = msg.user.id
        user_name = msg.user.name
        
        # Pes / iptal / vazgeç kontrolü
        if guess and guess.strip().lower() in ('pes', 'iptal', 'vazgeç', 'vazgec', 'quit', 'stop'):
            if user_id in self.guess_game_sessions:
                target = self.guess_game_sessions[user_id]['number']
                attempts = self.guess_game_sessions[user_id]['attempts']
                del self.guess_game_sessions[user_id]
                self.bot.send(f"🏳️ @{user_name} Pes ettin! Sayı {target} idi. ({attempts} tahmin yapmıştın)")
            else:
                self.bot.send(f"🎲 @{user_name} Zaten aktif bir oyunun yok.")
            return
        
        # İlk kez oynuyor - oyun başlat
        if user_id not in self.guess_game_sessions:
            target_number = random.randint(1, 100)
            self.guess_game_sessions[user_id] = {
                'number': target_number,
                'attempts': 0,
                'started': datetime.datetime.now()
            }
            
            # Eğer ilk komutla birlikte sayı verilmişse, oyunu başlat VE tahmini işle
            if guess and guess.strip():
                try:
                    guess_num = int(guess.strip())
                    if 1 <= guess_num <= 100:
                        session = self.guess_game_sessions[user_id]
                        session['attempts'] += 1
                        target = session['number']
                        
                        if guess_num == target:
                            del self.guess_game_sessions[user_id]
                            self.bot.send(f"🎉 @{user_name} İlk tahminde bildin! Sayı {target} idi! 🏆")
                            return
                        elif guess_num < target:
                            self.bot.send(f"🎲 @{user_name} 1-100 arası sayı tuttum! ⬆️ Daha BÜYÜK! (1. tahmin)")
                            return
                        else:
                            self.bot.send(f"🎲 @{user_name} 1-100 arası sayı tuttum! ⬇️ Daha KÜÇÜK! (1. tahmin)")
                            return
                except ValueError:
                    pass
            
            self.bot.send(f"🎲 @{user_name} 1-100 arası bir sayı tuttum!\nTahmin: !tahmin [sayı] | Çık: !tahmin pes")
            return
        
        if not guess or not guess.strip():
            attempts = self.guess_game_sessions[user_id]['attempts']
            self.bot.send(f"🎲 @{user_name} Hala oynuyorsun! ({attempts} tahmin)\nTahmin: !tahmin [sayı] | Çık: !tahmin pes")
            return
        
        try:
            guess_num = int(guess.strip())
        except ValueError:
            self.bot.send(f"🎲 @{user_name} Sayı gir! Örnek: !tahmin 50 | Çık: !tahmin pes")
            return
        
        if guess_num < 1 or guess_num > 100:
            self.bot.send(f"🎲 @{user_name} 1-100 arası sayı gir!")
            return
        
        session = self.guess_game_sessions[user_id]
        session['attempts'] += 1
        target = session['number']
        
        if guess_num == target:
            attempts = session['attempts']
            del self.guess_game_sessions[user_id]
            self.bot.send(f"🎉 @{user_name} DOĞRU! Sayı {target} idi!\n✅ {attempts} tahminde bildin!")
        elif guess_num < target:
            self.bot.send(f"⬆️ @{user_name} Daha BÜYÜK bir sayı! ({session['attempts']} tahmin)")
        else:
            self.bot.send(f"⬇️ @{user_name} Daha KÜÇÜK bir sayı! ({session['attempts']} tahmin)")
    
    # ==================== HABER BAŞLIKLARI ====================
    
    async def get_news_headlines(self):
        """Türkiye'den güncel haber başlıkları (RSS)"""
        try:
            # TRT Haber RSS feed
            url = "https://www.trthaber.com/sondakika_articles.rss"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        import xml.etree.ElementTree as ET
                        content = await response.text()
                        root = ET.fromstring(content)
                        
                        # İlk 5 haber başlığını al
                        items = root.findall('.//item')[:5]
                        headlines = []
                        
                        for item in items:
                            title = item.find('title')
                            if title is not None and title.text:
                                headlines.append(title.text.strip())
                        
                        return headlines if headlines else None
                    else:
                        print(f"⚠️ Haber RSS Error: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Haber RSS Exception: {e}")
            return None
    
    def news_cmd(self, msg):
        """Güncel haber başlıkları"""
        print(f"📰 Haber başlıkları istendi")
        
        try:
            headlines = self._run_async(self.get_news_headlines(), timeout=10)
            
            if headlines:
                message = "📰 Güncel Haberler:\n\n"
                for i, headline in enumerate(headlines, 1):
                    message += f"{i}. {headline}\n"
                self.bot.send(message.strip())
            else:
                self.bot.send("📰 Haber başlıkları alınamadı 😕")
        except Exception as e:
            print(f"⚠️ Haber hatası: {e}")
            self.bot.send("📰 Haber başlıkları alırken hata oluştu 😕")
    
    # ==================== İSİM ANLAMLARI ====================
    
    @staticmethod
    def _normalize_turkish(text):
        """Türkçe karakter normalizasyonu (araştırma için)"""
        replacements = {
            'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U', 'ş': 's', 'Ş': 'S',
            'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
        }
        for tr_char, ascii_char in replacements.items():
            text = text.replace(tr_char, ascii_char)
        return text
    
    def name_meaning_cmd(self, msg):
        """İsim anlamı ver (basit koleksiyon, Türkçe duyarsız eşleşme)"""
        groups = msg.groups
        name = groups[0] if groups[0] else groups[1] if groups[1] else None
        
        if not name or not name.strip():
            self.bot.send("🌟 Kullanım: !isim [isim]\nÖrnek: !isim Ahmet")
            return
        
        name_input = name.strip()
        
        # Popüler Türkçe isimlerin anlamları
        name_meanings = {
            'Ahmet': ('Övülmüş, övgüye layık', 'Arapça'),
            'Mehmet': ('Övülmüş, övgüye layık', 'Arapça'),
            'Mustafa': ('Seçilmiş, beğenilmiş', 'Arapça'),
            'Ali': ('Yüce, yüksek', 'Arapça'),
            'Hasan': ('Güzel, iyi', 'Arapça'),
            'Hüseyin': ('Güzel, yakışıklı', 'Arapça'),
            'Fatma': ('Sütten kesilmiş, olgun', 'Arapça'),
            'Ayşe': ('Yaşayan, hayat dolu', 'Arapça'),
            'Zeynep': ('Güzel kokulu ağaç', 'Arapça'),
            'Emine': ('Güvenilir, emin', 'Arapça'),
            'Can': ('Ruh, yaşam', 'Türkçe'),
            'Ece': ('Kraliçe, hanım', 'Türkçe'),
            'Ege': ('Değerli', 'Türkçe'),
            'Deniz': ('Okyanus', 'Türkçe'),
            'Yağmur': ('Gökten düşen su', 'Türkçe'),
            'Elif': ('Arap alfabesinin ilk harfi', 'Arapça'),
            'Ömer': ('Yaşayan, ömür', 'Arapça'),
            'Yusuf': ('Allah artırsın', 'İbranice'),
            'İbrahim': ('Ulu baba', 'İbranice'),
            'Meryem': ('İsyan eden, efendi', 'İbranice'),
            'Kemal': ('Olgunluk, kemâl', 'Arapça'),
            'Zehra': ('Parlak, aydınlık', 'Arapça'),
            'Burak': ('Şimşek gibi parlak', 'Arapça'),
            'Beren': ('Güçlü, akıllı', 'Türkçe'),
            'Asya': ('Doğu ülkesi', 'Yunanca'),
            'Defne': ('Zafer ağacı', 'Yunanca'),
            'Ela': ('Ela gözlü', 'Türkçe'),
            'Ada': ('Ada, kara parçası', 'Türkçe'),
            'Berk': ('Sağlam, güçlü', 'Türkçe'),
            'Arda': ('Tepeler, yükseklik', 'Türkçe'),
            'Miray': ('Prenses', 'Türkçe'),
            'Ecrin': ('Mükâfat, ödül', 'Arapça'),
            'Azra': ('Bakire, temiz', 'Arapça'),
            'Nehir': ('Irmak, akarsu', 'Türkçe'),
            'Yiğit': ('Cesur, kahraman', 'Türkçe'),
            'Kaan': ('Hükümdar, kağan', 'Türkçe'),
            'Doruk': ('Tepe, zirve', 'Türkçe'),
            'Görkem': ('İhtişam, görkemlilik', 'Türkçe'),
            'Selin': ('Sel gibi akan', 'Türkçe'),
            'Nil': ('Nil nehri', 'Mısırca'),
        }
        
        # Önce direkt eşleştirme dene (Title case)
        name_title = name_input.title()
        if name_title in name_meanings:
            meaning, origin = name_meanings[name_title]
            self.bot.send(f"🌟 {name_title}\n📖 Anlam: {meaning}\n🌍 Köken: {origin}")
            return
        
        # Türkçe karakter duyarsız fuzzy eşleştirme (ö→o, ş→s, ı→i vb.)
        input_normalized = self._normalize_turkish(name_input.lower())
        for db_name, (meaning, origin) in name_meanings.items():
            if self._normalize_turkish(db_name.lower()) == input_normalized:
                self.bot.send(f"🌟 {db_name}\n📖 Anlam: {meaning}\n🌍 Köken: {origin}")
                return
        
        self.bot.send(f"🌟 '{name_input}' isminin anlamı veritabanımızda yok 😕\nPopüler isimler için dene!")
    
    # ==================== DÖVİZ & KRİPTO - KOMUTLAR ====================
    
    def currency_cmd(self, msg):
        """Anlık döviz kurları"""
        print(f"💱 Döviz kurları istendi")
        
        try:
            currency_info = self._run_async(self.get_exchange_rates(), timeout=7)
            
            if currency_info:
                formatted = self.format_currency_info(currency_info)
                self.bot.send(formatted)
                print(f"✅ Döviz kurları gönderildi")
            else:
                self.bot.send("💱 Döviz verileri alınamadı. API'ye erişilemiyor 😕")
                print(f"⚠️ Döviz verileri alınamadı")
        except Exception as e:
            print(f"⚠️ Döviz hatası: {e}")
            self.bot.send("💱 Döviz verisi alırken hata oluştu 😕")
    
    def crypto_cmd(self, msg):
        """Anlık kripto para fiyatları"""
        print(f"₿ Kripto fiyatları istendi")
        
        try:
            crypto_info = self._run_async(self.get_crypto_prices(), timeout=7)
            
            if crypto_info:
                formatted = self.format_crypto_info(crypto_info)
                self.bot.send(formatted)
                print(f"✅ Kripto fiyatları gönderildi")
            else:
                self.bot.send("₿ Kripto verileri alınamadı. CoinGecko API'ye erişilemiyor 😕")
                print(f"⚠️ Kripto verileri alınamadı")
        except Exception as e:
            print(f"⚠️ Kripto hatası: {e}")
            self.bot.send("₿ Kripto verisi alırken hata oluştu 😕")
    
    # ==================== MÜZİK - KOMUTLAR ====================
    
    def music_cmd(self, msg):
        """Müzik arama komutu"""
        # Regex gruplarından query'yi al
        groups = msg.groups
        query = groups[0] if groups[0] else groups[1] if groups[1] else None
        
        if not query or not query.strip():
            self.bot.send("🎵 Kullanım: !müzik [şarkı/sanatçı adı]")
            return
        
        query = query.strip()
        print(f"🎵 Müzik aranıyor: '{query}'")
        
        try:
            music_list = self._run_async(self.search_music(query, 5), timeout=10)
            
            if music_list:
                formatted, url = self.format_music_results(music_list)
                
                if url:
                    self.bot.send_url(formatted, url)
                else:
                    self.bot.send(formatted)
                
                print(f"✅ Müzik sonuçları gönderildi: {query}")
            else:
                self.bot.send(f"🎵 '{query}' için müzik bulunamadı 🔍")
                print(f"⚠️ Müzik bulunamadı: '{query}'")
        except Exception as e:
            print(f"⚠️ Müzik arama hatası: {e}")
            self.bot.send("🎵 Müzik ararken hata oluştu 😕")
    
    # ==================== YARDIMCI ARAÇLAR - KOMUTLAR ====================
    
    def calc_cmd(self, msg):
        """Hesap makinesi komutu"""
        groups = msg.groups
        expression = groups[0] if groups[0] else groups[1] if groups[1] else None
        
        if not expression or not expression.strip():
            self.bot.send("🧮 Kullanım: !hesap [işlem]\nÖrnek: !hesap 2 + 2")
            return
        
        expression = expression.strip()
        print(f"🧮 Hesaplama: '{expression}'")
        
        result = self.calculate_expression(expression)
        
        if isinstance(result, str):  # Hata mesajı
            self.bot.send(f"🧮 {result}")
        else:
            # Sonucu formatla (ondalık sayıları düzgün göster)
            if isinstance(result, float):
                if result.is_integer():
                    result_str = str(int(result))
                else:
                    result_str = f"{result:.6f}".rstrip('0').rstrip('.')
            else:
                result_str = str(result)
            
            self.bot.send(f"🧮 {expression} = {result_str}")
            print(f"✅ Hesaplama sonucu: {result_str}")
    
    def translate_cmd(self, msg):
        """Çeviri komutu"""
        groups = msg.groups
        text = groups[0] if groups[0] else groups[1] if groups[1] else groups[2] if groups[2] else None
        
        if not text or not text.strip():
            self.bot.send("🌍 Kullanım: !çevir [metin]\nOtomatik dil algılama + Türkçe çeviri")
            return
        
        text = text.strip()
        
        # Çok uzun metinleri engelle
        if len(text) > 500:
            self.bot.send("🌍 Metin çok uzun! Max 500 karakter.")
            return
        
        print(f"🌍 Çeviri yapılıyor: '{text[:50]}...'")
        
        try:
            # Çeviri (Gemini veya Groq kullanır)
            if not self.ai_provider:
                self.bot.send("🌍 AI provider ayarlanmamış!")
                return
            
            prompt = f"Aşağıdaki metni Türkçe'ye çevir. Sadece çeviriyi yaz, başka bir şey yazma:\n\n{text}"
            
            translation = self._call_ai(
                messages=[
                    {"role": "system", "content": "Sen profesyonel bir çevirmensin. Verilen metni Türkçe'ye çevir. Sadece çeviriyi yaz, başka açıklama yapma."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Eğer çeviri orijinalle çok benzer (zaten Türkçe)
            if text.lower() in translation.lower() or translation.lower() in text.lower():
                self.bot.send(f"🌍 Bu metin zaten Türkçe görünüyor: {translation}")
            else:
                self.bot.send(f"🌍 Çeviri:\n{translation}")
            
            print(f"✅ Çeviri tamamlandı")
            
        except Exception as e:
            print(f"⚠️ Çeviri hatası: {e}")
            self.bot.send("🌍 Çeviri yaparken hata oluştu 😕")
    
    
    # ===============================================
    # OYUN BİLGİLERİ SİSTEMİ (RAWG API)
    # ===============================================
    
    async def search_game(self, query):
        """Wikipedia API kullanarak oyun arar (ücretsiz, API key gerektirmez)"""
        try:
            # Önce "(video oyunu)" ekleyerek ara (çoğu oyun bu şekilde)
            search_query = f"{query} (video oyunu)"
            game_info = await self.search_wikipedia(search_query)
            
            # Bulunamadıysa direkt oyun adıyla ara
            if not game_info:
                game_info = await self.search_wikipedia(query)
            
            # Hala bulunamadıysa "(oyun)" ile dene
            if not game_info:
                search_query = f"{query} (oyun)"
                game_info = await self.search_wikipedia(search_query)
            
            return game_info
        except Exception as e:
            print(f"⚠️ Oyun arama hatası: {e}")
            return None
    
    def format_game_results(self, game_info):
        """Oyun sonuçlarını formatlar (message, url) tuple döner"""
        if not game_info:
            return ("🎮 Oyun Wikipedia'da bulunamadı 🔍", None)
        
        # Wikipedia'dan gelen bilgiler
        title = game_info.get('title', 'Bilinmiyor')
        extract = game_info.get('extract', 'Bilgi yok')
        url = game_info.get('url', None)
        
        # Özeti kısalt (max 200 karakter)
        if len(extract) > 200:
            extract = extract[:197] + "..."
        
        # Mesaj formatı
        message = f"🎮 {title}\n\n{extract}"
        
        return (message, url)
    
    def detect_game_search(self, text):
        """Doğal dilde oyun arama algılar"""
        text_lower = text.lower()
        
        # Uzun isimli popüler oyunlar (substring eşleşmesi güvenli)
        long_game_names = [
            'minecraft', 'fortnite', 'valorant', 'cs go', 'csgo',
            'league of legends', 'warcraft', 'witcher',
            'cyberpunk', 'elden ring', 'call of duty',
            'pubg', 'apex legends', 'overwatch', 'zelda',
            'god of war', 'spider-man', 'assassin', 'red dead', 'skyrim'
        ]
        
        # Kısa isimli oyunlar - word boundary ile kontrol et (false positive önlemi)
        # 'cod' -> 'cod balığı' gibi yanlış eşleşmeleri önler
        short_game_names = ['gta', 'dota', 'fifa', 'pes', 'cod', 'mario']
        
        # Uzun isimler - substring eşleşmesi yeterli
        for game_name in long_game_names:
            if game_name in text_lower:
                return True
        
        # Kısa isimler - word boundary ile kontrol et
        for game_name in short_game_names:
            if re.search(r'\b' + re.escape(game_name) + r'\b', text_lower):
                # Ek kontrol: oyun/game bağlamında mı?
                game_context = ['oyun', 'game', 'oyna', 'play', 'hakkında', 'bilgi', 'nedir']
                if any(ctx in text_lower for ctx in game_context):
                    return True
        
        # "oyun" veya "game" kelimesi + bilgi arama kalıbı (sadece "oyun hakkında bilgi" gibi)
        game_keywords = ['oyun', 'game']
        search_keywords = ['hakkında', 'bilgi', 'nedir', 'nasıl', 'anlat', 'öner']
        
        has_game = any(keyword in text_lower for keyword in game_keywords)
        has_search = any(keyword in text_lower for keyword in search_keywords)
        
        return has_game and has_search
    
    def game_cmd(self, msg):
        """Oyun bilgisi komutu: !oyun [oyun adı]"""
        groups = msg.groups
        query = groups[0] if groups[0] else groups[1] if groups[1] else None
        
        if not query or not query.strip():
            self.bot.send("🎮 Kullanım: !oyun [oyun adı]\nÖrnek: !oyun minecraft")
            return
        
        query = query.strip()
        print(f"🎮 Oyun aranıyor: '{query}'")
        
        result = self._run_async(self._game_search_helper(query), timeout=10)
        if result:
            message, url = result
            if url:
                self.bot.send_url(message, url)
            else:
                self.bot.send(message)
        else:
            self.bot.send("🎮 Oyun bilgisi alınamadı 😕")
    
    async def _game_search_helper(self, query):
        """Oyun arama helper (async)"""
        game_info = await self.search_game(query)
        return self.format_game_results(game_info)
    
    
    # ===============================================
    # KİTAP BİLGİLERİ SİSTEMİ (Open Library API)
    # ===============================================
    
    async def search_book(self, query):
        """Open Library API kullanarak kitap arar"""
        try:
            # Open Library Search API (Free, no API key needed)
            encoded_query = urllib.parse.quote(query)
            url = f"https://openlibrary.org/search.json?q={encoded_query}&limit=3"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('docs', [])
                    else:
                        print(f"⚠️ Open Library API Error: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Open Library API Exception: {e}")
            return None
    
    def format_book_results(self, books):
        """Kitap sonuçlarını formatlar (message, url) tuple döner"""
        if not books:
            return ("📚 Kitap bulunamadı.", None)
        
        # İlk kitabı al (en relevantı)
        book = books[0]
        
        # Kitap bilgileri
        title = book.get('title', 'Bilinmiyor')
        
        # Yazar(lar)
        authors = book.get('author_name', [])
        author_text = ", ".join(authors[:2]) if authors else "Bilinmiyor"
        
        # Yıl
        year = book.get('first_publish_year', 'Belirtilmemiş')
        
        # Sayfa sayısı
        pages = book.get('number_of_pages_median')
        
        # Dil
        languages = book.get('language', [])
        lang_text = ""
        if 'tur' in languages:
            lang_text = " | Türkçe"
        elif 'eng' in languages:
            lang_text = " | İngilizce"
        
        # Open Library ID
        key = book.get('key', '')
        book_url = f"https://openlibrary.org{key}" if key else None
        
        # Mesaj formatı
        message = f"📚 {title}\n"
        message += f"✍️ Yazar: {author_text}\n"
        message += f"📅 Yıl: {year}"
        
        if pages:
            message += f" | 📖 {pages} sayfa"
        
        message += lang_text
        
        return (message, book_url)
    
    def detect_book_search(self, text):
        """Doğal dilde kitap arama algılar"""
        text_lower = text.lower()
        
        # Kitap anahtar kelimeleri + bilgi arama kalıbı gerekli
        book_keywords = ['kitap', 'book', 'roman', 'edebiyat', 'eser']
        search_keywords = ['hakkında', 'bilgi', 'nedir', 'öner', 'anlat', 'tavsiye']
        
        has_book = any(keyword in text_lower for keyword in book_keywords)
        has_search = any(keyword in text_lower for keyword in search_keywords)
        
        # Kitap + arama kelimesi birlikte olmalı
        if has_book and has_search:
            return True
        
        # Popüler kitaplar / yazarlar - sadece kitap bağlamında eşleşsin
        # ("1984 yılında" gibi false positive'leri önlemek için bağlam kontrolü)
        popular_books = [
            'suç ve ceza', 'sefiller', 'beyaz diş',
            'hayvan çiftliği', 'simyacı',
            'harry potter', 'hobbit', 'yüzüklerin efendisi',
            'tutunamayanlar', 'masumiyet müzesi'
        ]
        
        popular_authors = [
            'dostoyevski', 'tolstoy', 'kafka', 'orwell', 'coelho',
            'sabahattin ali', 'oğuz atay', 'orhan pamuk', 'elif şafak'
        ]
        
        # Popüler kitap/yazar varsa + kitap bağlamı varsa true
        book_context_words = ['kitap', 'book', 'roman', 'oku', 'yazar', 'hakkında', 'bilgi', 'nedir', 'öner', 'tavsiye']
        has_context = any(ctx in text_lower for ctx in book_context_words)
        
        if has_context:
            for book_name in popular_books:
                if book_name in text_lower:
                    return True
            for author_name in popular_authors:
                if author_name in text_lower:
                    return True
        
        return False
    
    def book_cmd(self, msg):
        """Kitap bilgisi komutu: !kitap [kitap adı]"""
        groups = msg.groups
        query = groups[0] if groups[0] else groups[1] if groups[1] else None
        
        if not query or not query.strip():
            self.bot.send("📚 Kullanım: !kitap [kitap adı]\nÖrnek: !kitap suç ve ceza")
            return
        
        query = query.strip()
        print(f"📚 Kitap aranıyor: '{query}'")
        
        result = self._run_async(self._book_search_helper(query), timeout=10)
        if result:
            message, url = result
            if url:
                self.bot.send_url(message, url)
            else:
                self.bot.send(message)
        else:
            self.bot.send("📚 Kitap bilgisi alınamadı 😕")
    
    async def _book_search_helper(self, query):
        """Kitap arama helper (async)"""
        books = await self.search_book(query)
        return self.format_book_results(books)
