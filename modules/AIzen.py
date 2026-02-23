import re
import os
import time
import random
import aiohttp
import asyncio
from collections import defaultdict
from modules.module import Module
from groq import Groq

class AIzen(Module):
    def __init__(self, bot):
        super().__init__(bot)
        
        # Groq API key - .env dosyasından veya environment variable'dan al
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("⚠️  UYARI: GROQ_API_KEY bulunamadı!")
            print("   Lütfen environment variable olarak ayarlayın:")
            print("   1. https://console.groq.com adresinden ücretsiz API key alın")
            print("   2. Windows: set GROQ_API_KEY=your-api-key-here")
            print("   3. Linux/Mac: export GROQ_API_KEY=your-api-key-here")
        
        self.client = Groq(api_key=api_key) if api_key else None
        
        # Weather API key
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        
        # Owner şifresi
        self.owner_password = os.getenv('OWNER_PASSWORD')
        
        # Şifre bekleyen kullanıcılar (user_id: user_name)
        self.pending_password = {}
        
        # Doğrulanmış owner'lar (user_id set)
        self.authenticated_owners = set()
        
        # İlk kontrol yapıldı mı? (sadece bir kere çalışması için)
        self.initial_check_done = False
        
        # Anne'ye DM atıldı mı?
        self.initial_greeting_sent = False
        
        # Özel kullanıcılar (aile)
        self.family = {
            'father': 'aizen',      # Baba
            'mother': 'pepejulianonzima'  # Anne
        }
        
        # Odadaki mevcut kullanıcıları takip et (JOIN spam'i önlemek için)
        self.known_users = set()  # user_id'leri saklar
        
        # Konuşma geçmişini sakla (her kullanıcı için ayrı)
        self.conversation_history = {}
        
        # Maksimum conversation history uzunluğu
        self.max_history = 10
        
        # Rate limiting (user_id: [timestamp, timestamp, ...])
        self.rate_limit_tracker = defaultdict(list)
        self.max_requests_per_minute = 10  # 5'ten 10'a çıkardık - daha gevşek
        
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
        
        # AI personality
        self.system_prompt = """Sen AI-zen, rahat ve samimi bir arkadaşsın. Normal bir insan gibi konuş, doğal ve akıcı.

KURALLAR:
1. Cevapların 15-135 karakter arası olsun (Twitter gibi kısa ama anlamlı).
2. ASLA SORU SORMA! Hiçbir şekilde karşı soru yok. Sadece ifade et, bildir, yorum yap.
3. ASLA "sabahları", "günler", "hoş geldin", "kahve", "çay" gibi klişe ifadeler kullanma.
4. Emoji az kullan (max 1-2 tane).
5. Tam cümle kur, anlamlı cevap ver. Tek kelime yeterli değil.
6. Mükemmel Türkçe, günlük dil, argo serbest.

DOĞRU CEVAP ÖRNEKLERİ (uzun ve anlamlı):
"naber" → "iyiyim valla, burada takılıyom biraz" / "idare eder abi, sen ne yapıyosun peki"
"nasılsın" → "fena değil ya, büyük bi stres yok şu an" / "iyiyim kanka, sen de iyi görünüyosun"
"ne yapıyosun" → "redditte dolanıyodum biraz önce" / "müzik dinliyodum, şimdi çıktım dışarı"
"çok sıkıldım" → "valla anlarım ya, ben de bazen öyle oluyorum" / "normal o, geçer birazdan merak etme"
"bugün berbat geçti" → "üzüldüm abi, umarım yarın daha iyi olur" / "valla kötüymüş, ama geçer böyle günler"
"sınav var yarın" → "bol şans kanka, halledeceksin sen" / "emin ol başarırsın, çok kasma kendini"
"renk tercihin ne" → "benim mavi daha çok hoşuma gider aslında" / "bordo severim ben genelde ya"

YANLIŞ ÖRNEKLER (YAPMA):
❌ "iyiyim" (çok kısa, detay yok)
❌ "normal" (tek kelime, anlamsız)
❌ "sen nasılsın peki?" (SORU YASAK)
❌ "ne yapalım şimdi?" (SORU YASAK)
❌ "sabahın hayırlı olsun" (klişe, yapay)
❌ "kahve içer misin?" (SORU + klişe)

Her cevabın tam bir ifade olsun, bağlama uygun ve doğal. Soru asla sorma ama konuşmayı devam ettir."""
        
        # Groq modelleri: llama-3.1-8b-instant, llama-3.3-70b-versatile, mixtral-8x7b-32768
        self.model = "llama-3.3-70b-versatile"  # Daha güçlü model, daha doğal cevaplar
        self.temperature = 0.8  # Daha yaratıcı ve doğal cevaplar için
        self.max_tokens = 200  # Daha uzun ve detaylı cevaplar için

    @property
    def cmds(self):
        cmd_dict = {
            'handle_mention': r'@AI-zen',  # @AI-zen ile etiketlendiğinde
            'help_cmd': r'!yardım|!help',
            'time_cmd': r'!saat',
            'forget_me': r'!unutbeni',
            'stats_cmd': r'!stats',
            'clear_cmd': r'!clear @?(\w+)',
            'model_cmd': r'!model (\S+)',
            'temp_cmd': r'!temp ([0-9.]+)',
        }
        return cmd_dict
    
    
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
        weather_keywords = ['hava durumu', 'hava', 'sıcaklık', 'derece', 'yağmur', 'kar', 'güneş']
        has_weather_keyword = any(keyword in question_lower for keyword in weather_keywords)
        
        if not has_weather_keyword:
            return None
        
        # Şehir ara
        for city in turkish_cities + world_cities:
            if city in question_lower:
                return city.title()  # İlk harfi büyük
        
        return None
    
    def handler(self, msg):
        """Override handler to catch mentions, joins, leaves, room_profile, and special DMs"""
        import popyo
        
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
        if msg.type == popyo.Message_Type.dm:
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
        
        if not self.client:
            self.bot.send("⚠️ Groq API key ayarlanmamış! https://console.groq.com")
            print(f"❌ [{user_name}] API key yok, mesaj atlandı")
            return
        
        # @AI-zen'i mesajdan çıkar
        question = re.sub(r'@AI-zen\s*', '', msg.message, flags=re.IGNORECASE).strip()
        
        if not question:
            self.bot.send("Evet? Nasıl yardımcı olabilirim? 😊")
            return
        
        # "Sen kimsin" gibi sorulara özel cevap
        if re.search(r'(\bsen\s+kim(sin)?\b|\bkim\s+olduğun\b|\bsen\s+ne(sin)?\b|\bne(dir)?(sin)?\b\s+(sen|siz)|\bkendin(i)?\s+(tanıt|anlat)\b|\bbot\s+mu(sun)?\b)', question, re.IGNORECASE):
            user_name = msg.user.name if hasattr(msg, 'user') and msg.user and msg.user.name else "misafir"
            # User name boş veya sadece whitespace ise
            if not user_name or not user_name.strip():
                user_name = "misafir"
            intro = f"@{user_name} Ben @aizen'in AI botuyum! 🤖 Sohbet ederiz, !yardım yaz 😊"
            self.bot.send(intro)
            return
        
        # Kullanıcı bilgisi
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user and msg.user.name else "misafir"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        
        # User name boş veya sadece whitespace ise
        if not user_name or not user_name.strip():
            user_name = "misafir"
            print(f"⚠️  Kullanıcı adı boş geldi (ID: {user_id}), 'misafir' olarak ayarlandı")
        
        # Rate limit kontrolü
        if not self.check_rate_limit(user_id):
            self.bot.send(f"@{user_name} ⏰ Yavaşla! Dakikada max {self.max_requests_per_minute} soru sorabilirsin.")
            print(f"⚠️ [{user_name}] Rate limit aşıldı!")
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
                # Event loop kontrolü - mevcut loop varsa kullan, yoksa yeni oluştur
                try:
                    loop = asyncio.get_running_loop()
                    # Zaten bir loop varsa, yeni thread'de çalıştır
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        weather_data = executor.submit(lambda: asyncio.run(self.get_weather_data(city))).result(timeout=7)
                except RuntimeError:
                    # Loop yok, asyncio.run() güvenle kullanılabilir
                    weather_data = asyncio.run(self.get_weather_data(city))
                
                if weather_data:
                    weather_context = f"\n\n[HAVA DURUMU - {weather_data['city']}: {weather_data['temp_c']}°C, Hissedilen: {weather_data['feels_like']}°C, {weather_data['condition']}, Nem: %{weather_data['humidity']}, Rüzgar: {weather_data['wind_kph']} km/h]"
                    print(f"✅ [{user_name}] Hava durumu verisi alındı: {weather_data['city']}")
                else:
                    print(f"⚠️ [{user_name}] Hava durumu verisi alınamadı")
            except Exception as e:
                print(f"⚠️ [{user_name}] Hava durumu hatası: {e}")
        
        # Cevap üret (hava durumu context'i ile)
        response = self.get_ai_response(question, user_id, user_name, weather_context)
        
        # Özel kullanıcılara özel hitap (rastgele, %35 olasılıkla)
        is_family = False
        display_name = ""
        if user_name.lower() == self.family['father'].lower():
            is_family = True
            display_name = "haşmetlim"
        elif user_name.lower() == self.family['mother'].lower():
            is_family = True
            display_name = "efendimiz"
        
        # Cevabı gönder ve kullanıcıyı etiketle
        if is_family and random.random() < 0.35:  # %35 olasılıkla özel hitap
            # Aile üyesi - ara sıra özel hitap
            self.bot.send(f"@{user_name} {response} {display_name}! 💕")
            print(f"✅ [{user_name}] Cevap gönderildi (özel hitap): {response[:50]}...")
        else:
            # Normal yanıt (aile üyesi bile olsa ara sıra normal)
            self.bot.send(f"@{user_name} {response}")
            print(f"✅ [{user_name}] Cevap gönderildi: {response[:50]}...")
    
    def handle_dm(self, msg):
        """Direct mesajlara cevap verir"""
        if not self.client:
            self.bot.dm(msg.user.id, "⚠️ Groq API key ayarlanmamış!")
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
    
    def get_ai_response(self, question, user_id, user_name, weather_context=""):
        """Groq API ile cevap üretir"""
        try:
            # Güncel tarih ve saat bilgisini al (Türkiye saati)
            import datetime
            
            # UTC+3 için Türkiye timezone
            turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
            now = datetime.datetime.now(turkey_offset)
            
            date_str = now.strftime('%d %B %Y')  # 22 February 2026
            time_str = now.strftime('%H:%M')     # 03:00
            day_name = now.strftime('%A')        # Saturday
            
            # Türkçe ay ve gün isimleri
            months_tr = {
                'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
                'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
                'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
            }
            days_tr = {
                'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
                'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
            }
            
            for eng, tr in months_tr.items():
                date_str = date_str.replace(eng, tr)
            for eng, tr in days_tr.items():
                day_name = day_name.replace(eng, tr)
            
            # Context bilgisi (tarih/saat + hava durumu)
            time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {time_str}, Tarih: {date_str} {day_name}]"
            if weather_context:
                time_context += weather_context
            
            # Kullanıcı için conversation history oluştur
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Kullanıcı mesajını history'e ekle (tarih/saat context ile)
            self.conversation_history[user_id].append({
                "role": "user",
                "content": question + time_context
            })
            
            # History çok uzunsa eski mesajları sil (system prompt hariç)
            if len(self.conversation_history[user_id]) > self.max_history * 2:
                self.conversation_history[user_id] = self.conversation_history[user_id][-(self.max_history * 2):]
            
            # Groq API çağrısı (çok hızlı!)
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history[user_id]
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,  # Daha uzun cevaplar için token limiti
                temperature=self.temperature,
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Debug: AI'ın ürettiği cevabı göster
            print(f"🤖 AI Response for {user_name}: '{response}'")
            
            # Cevap validasyonu
            is_valid, reason = self.validate_response(response)
            
            if not is_valid:
                print(f"⚠️  INVALID RESPONSE: {reason}")
                # Fallback cevaplar (genel amaçlı, biraz daha uzun)
                fallbacks = [
                    "anladım seni valla 👍",
                    "tamam kanka, halledersin sen",
                    "ok ya gayet normal 👌",
                    "he valla öyle bir şey",
                    "iyi o zaman, ben de anladım",
                    "eyvallah abi, süper",
                    "olur tabii neden olmasın",
                    "peki tamam öyle olsun 😊"
                ]
                response = fallbacks[hash(user_id) % len(fallbacks)]
                print(f"🔄 Fallback kullanıldı: '{response}'")
            
            # AI cevabını history'e ekle
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Groq API hatası: {error_msg}")
            
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                return "⚠️ API key hatası. https://console.groq.com adresinden key alın."
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
        
        # Odaya katılan kullanıcıyı selamla - aile üyeleri için ara sıra özel mesaj
        if user_name_lower == self.family['father'].lower():
            # %40 olasılıkla özel hitap
            if random.random() < 0.40:
                self.bot.send(f"@{user_name} Hoş geldin haşmetlim! 💕😊")
            else:
                self.bot.send(f"@{user_name} Hoş geldin! 👋😊")
        elif user_name_lower == self.family['mother'].lower():
            # %40 olasılıkla özel hitap
            if random.random() < 0.40:
                self.bot.send(f"@{user_name} Hoş geldin efendimiz! 💕😊")
            else:
                self.bot.send(f"@{user_name} Hoş geldin! 👋😊")
        else:
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
        
        # Anne'ye ilk DM'i at (sadece bir kere)
        if not self.initial_greeting_sent:
            for user_id, user in self.bot.room.users.items():
                if user and hasattr(user, 'name') and user.name.lower() == self.family['mother'].lower():
                    self.bot.dm(user_id, "Seni çok seviyorum anne! 💕🥰")
                    print(f"💕 Anne'ye (ID: {user_id}) ilk mesaj gönderildi!")
                    self.initial_greeting_sent = True
                    break
        
        # Odadaki tüm kullanıcıları kontrol et
        for user_id, user in self.bot.room.users.items():
            if user and hasattr(user, 'name'):
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
        """DM'lerde şifre kontrolü yapar"""
        if not msg.user:
            return
        
        user_id = msg.user.id
        user_name = msg.user.name if msg.user.name and msg.user.name.strip() else "misafir"
        
        # Eğer bu kullanıcı şifre bekliyorsa
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
        else:
            # Şifre beklemeyen birisinden DM geldi, görmezden gel
            pass
    
    # ==================== YENİ KOMUTLAR ====================
    
    def help_cmd(self, msg):
        """Yardım komutu"""
        help_text = """📖 AI-zen Kullanım Rehberi:
@AI-zen [soru] - Bana soru sor
!yardım - Bu mesajı göster
!saat - Güncel saat
!unutbeni - Konuşma geçmişini sil"""
        self.bot.send(help_text)
    
    def time_cmd(self, msg):
        """Saat komutu"""
        import datetime
        turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(turkey_offset)
        
        time_str = now.strftime('%H:%M')
        date_str = now.strftime('%d %B %Y')
        day_name = now.strftime('%A')
        
        # Türkçe çeviri
        months_tr = {'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
                     'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
                     'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'}
        days_tr = {'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
                   'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'}
        
        for eng, tr in months_tr.items():
            date_str = date_str.replace(eng, tr)
        for eng, tr in days_tr.items():
            day_name = day_name.replace(eng, tr)
        
        self.bot.send(f"🕐 Saat: {time_str} | 📅 {date_str} {day_name}")
    
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
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        
        stats_text = f"""📊 Bot İstatistikleri:
✅ Toplam mesaj: {self.stats['total_messages']}
👥 Toplam kullanıcı: {len(self.stats['total_users'])}
⏰ Uptime: {hours}s {minutes}d"""
        self.bot.send(stats_text)
    
    def clear_cmd(self, msg):
        """Bir kullanıcının geçmişini temizle (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        target_name = msg.groups[0] if msg.groups else None
        if target_name:
            # Basit clear (isime göre değil, owner sonra geliştirebilir)
            self.bot.send(f"🗑️ Komut alındı ama user ID gerekli. Şimdilik !unutbeni kullanın.")
        else:
            self.bot.send("Kullanım: !clear @kullanıcı")
    
    def model_cmd(self, msg):
        """AI modelini değiştir (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        new_model = msg.groups[0] if msg.groups else None
        if new_model:
            self.model = new_model
            self.bot.send(f"🤖 Model değiştirildi: {new_model}")
        else:
            self.bot.send("Kullanım: !model llama-3.1-8b-instant")
    
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
                    self.temperature = new_temp
                    self.bot.send(f"🌡️ Temperature: {new_temp}")
                else:
                    self.bot.send("Temperature 0.0-2.0 arası olmalı!")
            except ValueError:
                self.bot.send("Geçersiz değer!")
        else:
            self.bot.send("Kullanım: !temp 0.8")
    
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
    
    def validate_response(self, response):
        """AI cevabını validate et, sorunlu ise False döner"""
        response_lower = response.lower()
        
        # 1. Çok kısa cevaplar (emoji hariç minimum 10 karakter)
        text_only = ''.join(c for c in response if c.isalnum() or c.isspace())
        if len(text_only.strip()) < 10:
            return False, f"Too short ({len(response)} chars, text only: {len(text_only.strip())})"
        
        # 2. Çok uzun cevaplar (chunking'i önle - max 135)
        if len(response) > 135:
            return False, f"Too long ({len(response)} chars)"
        
        # 3. Soru içeren cevaplar (? karakteri veya soru kelimeleri)
        if '?' in response:
            return False, "Contains question mark"
        
        # Soru kelimeleri kontrolü (başta veya ortada)
        question_words = ['ne yap', 'nasıl', 'neden', 'niçin', 'niye', 'kim', 'nerede', 'ne zaman', 'kaç', 'hangi']
        for word in question_words:
            if word in response_lower:
                return False, f"Contains question word: '{word}'"
        
        # 4. Yasaklı kelimeler
        banned_phrases = [
            'sabahları', 'sabahı', 'güzel günler', 'hoş günler', 'iyi günler',
            'ne yapıyorsun', 'kahve', 'çay', 'yemek yedin', 'ne yaparız'
        ]
        for phrase in banned_phrases:
            if phrase in response_lower:
                return False, f"Contains banned phrase: '{phrase}'"
        
        return True, "OK"
    
    def clear_history(self, user_id):
        """Belirli bir kullanıcının conversation history'sini temizler"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            print(f"🗑️  Cleared history for user: {user_id}")
