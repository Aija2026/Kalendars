import os
import json
import time
import threading
import datetime
import imaplib
import email
import webbrowser
import unicodedata
import re
import customtkinter as ctk
import anthropic
from ics import Calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- KONFIGURĀCIJA ---
SETTINGS_FILE = "user_settings.json"
DB_FILE = "processed_ids.txt"
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVERS = {
    "Inbox.lv": "mail.inbox.lv",
    "Gmail": "imap.gmail.com",
    "Outlook": "outlook.office365.com"
}

class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, master, service, summary, start_iso, end_iso=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Apstiprinājums")
        self.geometry("400x420")
        self.service = service
        self.summary = summary
        self.start_iso = start_iso
        self.end_iso = end_iso
        self.result = None
        self.duration = 60
        self.grab_set()
        self.attributes("-topmost", True)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(main_frame, text="Jauns pasākums", font=("Roboto Medium", 18)).pack(pady=(0, 15))
        
        info_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(info_frame, text=summary, font=("Arial", 14, "bold"), wraplength=340).pack(pady=(15, 5), padx=15)
        
        start_dt = datetime.datetime.fromisoformat(start_iso.replace('Z', ''))
        ctk.CTkLabel(info_frame, text=f"Sākums: {start_dt.strftime('%d.%m.%Y %H:%M')}", font=("Arial", 12)).pack(pady=(5, 15), padx=15)

        self.conflict_label = ctk.CTkLabel(main_frame, text="", text_color="#E67E22", font=("Arial", 11, "bold"), wraplength=350)
        self.conflict_label.pack(pady=5)

        if not self.end_iso:
            self.dur_combo = ctk.CTkComboBox(main_frame, values=["15 min", "30 min", "45 min", "1 h", "1.5 h", "2 h", "3 h"], command=self.check_conflicts, width=150)
            self.dur_combo.set("1 h")
            self.dur_combo.pack(pady=10)
        else:
            end_dt = datetime.datetime.fromisoformat(end_iso.replace('Z', ''))
            ctk.CTkLabel(main_frame, text=f"Beigas: {end_dt.strftime('%H:%M')}", text_color="#3498db").pack(pady=10)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=(20, 0))
        ctk.CTkButton(btn_frame, text="Pievienot", fg_color="#2ecc71", width=120, command=self.on_yes).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Atmest", fg_color="#e74c3c", width=120, command=self.on_no).pack(side="left", padx=10)
        self.check_conflicts()

    def check_conflicts(self, _=None):
        try:
            if self.end_iso: t_max = self.end_iso
            else:
                m = {"15 min": 15, "30 min": 30, "45 min": 45, "1 h": 60, "1.5 h": 90, "2 h": 120, "3 h": 180}
                dur = m.get(self.dur_combo.get(), 60)
                start_dt = datetime.datetime.fromisoformat(self.start_iso.replace('Z', ''))
                t_max = (start_dt + datetime.timedelta(minutes=dur)).isoformat() + "+02:00"
            res = self.service.events().list(calendarId='primary', timeMin=self.start_iso, timeMax=t_max, singleEvents=True).execute()
            if res.get('items'): self.conflict_label.configure(text=f"⚠️ Konflikts ar: {res.get('items')[0].get('summary')}")
            else: self.conflict_label.configure(text="✅ Laiks ir brīvs")
        except: pass

    def on_yes(self): self.result = True; self.destroy()
    def on_no(self): self.result = False; self.destroy()

class CalendarApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = self.load_settings()
        ctk.set_appearance_mode(self.settings.get("appearance", "System"))
        ctk.set_default_color_theme(self.settings.get("theme", "blue"))
        
        self.title("Aģents v5.2")
        self.geometry("500x750")
        
        self.processed_emails = self.load_processed_ids()
        self.ai_client = None
        self.dialog_lock = threading.Lock()
        
        # UI
        style_frame = ctk.CTkFrame(self, height=40)
        style_frame.pack(pady=(10, 0), padx=20, fill="x")
        self.app_mode = ctk.CTkOptionMenu(style_frame, values=["System", "Dark", "Light"], command=self.change_appearance, width=100)
        self.app_mode.set(self.settings.get("appearance", "System"))
        self.app_mode.pack(side="right", padx=10, pady=5)
        
        settings_frame = ctk.CTkFrame(self, corner_radius=15)
        settings_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(settings_frame, text="Iestatījumi", font=("Arial", 14, "bold")).pack(pady=10)

        # AI Atslēga
        ctk.CTkLabel(settings_frame, text="Claude API Key:").pack(anchor="w", padx=20)
        self.ai_entry = ctk.CTkEntry(settings_frame, placeholder_text="sk-ant-api...", show="*", width=350)
        self.ai_entry.insert(0, self.settings.get("ai_key", ""))
        self.ai_entry.pack(pady=5, padx=20)

        self.provider_var = ctk.StringVar(value=self.settings.get("provider", "Inbox.lv"))
        self.provider_menu = ctk.CTkOptionMenu(settings_frame, values=list(SERVERS.keys()), variable=self.provider_var, width=350)
        self.provider_menu.pack(pady=5)

        self.email_entry = ctk.CTkEntry(settings_frame, placeholder_text="E-pasta adrese", width=350)
        self.email_entry.insert(0, self.settings.get("email", ""))
        self.email_entry.pack(pady=5)

        self.pass_entry = ctk.CTkEntry(settings_frame, placeholder_text="Lietotnes parole", show="*", width=350)
        self.pass_entry.insert(0, self.settings.get("password", ""))
        self.pass_entry.pack(pady=(5, 15))

        self.btn_save = ctk.CTkButton(self, text="STARTĒT AGENTU", command=self.start_sync, fg_color="#2ecc71", height=45)
        self.btn_save.pack(pady=15, padx=20, fill="x")

        status_frame = ctk.CTkFrame(self, corner_radius=10)
        status_frame.pack(pady=(0, 20), padx=20, fill="both", expand=True)
        self.status_box = ctk.CTkTextbox(status_frame, font=("Consolas", 11))
        self.status_box.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.service = None
        self.running = False

    def change_appearance(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.settings["appearance"] = new_mode
        self.save_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
        return {"appearance": "System", "theme": "blue"}

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f: json.dump(self.settings, f)

    def load_processed_ids(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f: return set(line.strip() for line in f)
        return set()

    def save_processed_id(self, m_id):
        self.processed_emails.add(m_id)
        with open(DB_FILE, "a") as f: f.write(f"{m_id}\n")

    def log(self, text):
        self.status_box.insert("end", f"[{datetime.datetime.now().strftime('%H:%M')}] {text}\n")
        self.status_box.see("end")

    def get_google_service(self):
        creds = None
        if os.path.exists('token.json'): creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token: token.write(creds.to_json())
        return build('calendar', 'v3', credentials=creds)

    def sync_logic(self):
        user, pwd, ai_key = self.email_entry.get(), self.pass_entry.get(), self.ai_entry.get()
        if not ai_key:
            self.log("❌ Kļūda: Ievadiet Claude API atslēgu!"); self.running = False
            self.btn_save.configure(state="normal", text="Mēģināt vēlreiz"); return
        
        self.ai_client = anthropic.Anthropic(api_key=ai_key.strip())
        srv = SERVERS[self.provider_var.get()]
        self.settings.update({"provider": self.provider_var.get(), "email": user, "password": pwd, "ai_key": ai_key})
        self.save_settings()

        try:
            self.log("🔗 Savienojos..."); self.service = self.get_google_service()
            mail = imaplib.IMAP4_SSL(srv); mail.login(user, pwd)
            while self.running:
                mail.select("INBOX")
                _, data = mail.search(None, f'(SINCE "{datetime.datetime.now().strftime("%d-%b-%Y")}")')
                for m_id in data[0].split()[-10:]:
                    m_id_str = m_id.decode()
                    if m_id_str in self.processed_emails: continue
                    _, msg_data = mail.fetch(m_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Loģika e-pastu apstrādei (ICS vai AI)
                    # ... (iepriekšējā ICS/AI loģika paliek tā pati) ...
                    event_data = None
                    for part in msg.walk():
                        if part.get_content_type() in ['text/calendar', 'application/ics']:
                            try:
                                ics_data = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                c = Calendar(ics_data); e = list(c.events)[0]
                                event_data = {'summary': e.name, 'start': e.begin.isoformat(), 'end': e.end.isoformat()}
                            except: pass
                    
                    if not event_data:
                        body = ""
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain": body = p.get_payload(decode=True).decode('utf-8', 'replace'); break
                        if len(body.strip()) > 10:
                            prompt = f"Extract event from: '{body[:500]}'. Return ONLY JSON: {{'summary': '...', 'start': 'ISO'}}"
                            res = self.ai_client.messages.create(model="claude-3-haiku-20240307", max_tokens=200, system="JSON only.", messages=[{"role": "user", "content": prompt}])
                            event_data = json.loads(re.search(r'\{.*\}', res.content[0].text).group(0))
                            if '+' not in event_data['start']: event_data['start'] += "+02:00"

                    if event_data:
                        with self.dialog_lock:
                            done = threading.Event()
                            def ask():
                                d = ConfirmationDialog(self, self.service, event_data['summary'], event_data['start'], event_data.get('end'))
                                self.wait_window(d)
                                if d.result is True:
                                    e_iso = event_data.get('end') or (datetime.datetime.fromisoformat(event_data['start'].replace('Z','')) + datetime.timedelta(minutes=d.duration)).isoformat() + "+02:00"
                                    self.service.events().insert(calendarId='primary', body={'summary': event_data['summary'], 'start': {'dateTime': event_data['start']}, 'end': {'dateTime': e_iso}}).execute()
                                    self.log(f"✅ OK: {event_data['summary']}"); self.save_processed_id(m_id_str)
                                elif d.result is False:
                                    self.log(f"❌ Atmests: {event_data['summary']}"); self.save_processed_id(m_id_str)
                                done.set()
                            self.after(0, ask); done.wait()
                self.log("🛌 Gaidu jaunus e-pastus..."); time.sleep(120) 
        except Exception as e:
            self.log(f"❌ Kļūda: {e}"); self.running = False
            self.btn_save.configure(state="normal", text="Mēģināt vēlreiz")

    def start_sync(self):
        if not self.running:
            self.running = True
            self.btn_save.configure(state="disabled", text="AGENTS STRĀDĀ...")
            threading.Thread(target=self.sync_logic, daemon=True).start()

if __name__ == "__main__":
    app = CalendarApp(); app.mainloop()