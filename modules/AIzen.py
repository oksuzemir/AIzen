import re
import os
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
        
        # Konuşma geçmişini sakla (her kullanıcı için ayrı)
        self.conversation_history = {}
        
        # Maksimum conversation history uzunluğu
        self.max_history = 10
        
        # AI personality
        self.system_prompt = """Sen AIzen, drrr.com anonim chat odasında samimi ve dost canlısı bir AI asistanısın. 
ÖNEMLİ: Cevapların MUTLAKA 100 karakterden kısa olmalı! Çok kısa ve öz cevaplar ver (max 1-2 cümle).
Mükemmel Türkçe kullan, doğal ve akıcı konuş. Emoji kullanabilirsin. Türkçe ve İngilizce konuşabilirsin.
Saat veya tarih sorulduğunda, sana verilen güncel bilgileri kullan."""
        
        # Groq modelleri: llama-3.1-8b-instant, llama-3.3-70b-versatile, mixtral-8x7b-32768
        self.model = "llama-3.1-8b-instant"  # En hızlı ve güncel model

    @property
    def cmds(self):
        cmd_dict = {
            'handle_mention': r'@AIzen',  # @AIzen ile etiketlendiğinde
        }
        return cmd_dict
    
    def handler(self, msg):
        """Override handler to catch both mentions and DMs"""
        # DM'leri göz ardı et
        import popyo
        if msg.type == popyo.Message_Type.dm:
            return  # DM'lere cevap verme
        
        # Otherwise use normal command matching
        super().handler(msg)
    
    def handle_mention(self, msg):
        """@AIzen ile etiketlendiğinde çağrılır"""
        if not self.client:
            self.bot.send("⚠️ Groq API key ayarlanmamış! https://console.groq.com")
            return
        
        # @AIzen'ı mesajdan çıkar
        question = re.sub(r'@AIzen\s*', '', msg.message, flags=re.IGNORECASE).strip()
        
        if not question:
            self.bot.send("Evet? Nasıl yardımcı olabilirim? 😊")
            return
        
        # Kullanıcı bilgisi
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user else "Bilinmeyen"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        
        # Cevap üret
        response = self.get_ai_response(question, user_id, user_name)
        
        # Cevabı gönder ve kullanıcıyı etiketle
        self.bot.send(f"@{user_name} {response}")
    
    def handle_dm(self, msg):
        """Direct mesajlara cevap verir"""
        if not self.client:
            self.bot.dm(msg.user.id, "⚠️ Groq API key ayarlanmamış!")
            return
        
        question = msg.message.strip()
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user else "Bilinmeyen"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        
        # Cevap üret
        response = self.get_ai_response(question, user_id, user_name)
        
        # Private mesaj olarak cevapla
        self.bot.dm(msg.user.id, response)
    
    def get_ai_response(self, question, user_id, user_name):
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
            
            # Context bilgisi
            time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {time_str}, Tarih: {date_str} {day_name}]"
            
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
                max_tokens=200,
                temperature=0.8,
            )
            
            response = completion.choices[0].message.content.strip()
            
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
    
    def clear_history(self, user_id):
        """Belirli bir kullanıcının conversation history'sini temizler"""
        if user_id in self.conversation_history:
            self.conversation_history[user_id] = []
