
# ==========================================================
# PERSONAL USE CASE: 
# My primary email for job searching is Inbox.lv, 
# while personal events are on Gmail. 
# ----------------------------------------------------------
# PROBLEM: Schedules often overlap, leading to conflicts.
# SOLUTION: This AI Agent unifies all Inbox.lv events into 
#           one Google Calendar automatically.
# RESULT: Zero manual entry and a perfectly synced schedule!
# ==========================================================
import os, json, time, threading, datetime, imaplib, email, webbrowser, re
import customtkinter as ctk
import anthropic
from ics import Calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SETTINGS_FILE = "user_settings.json"
DB_FILE = "processed_ids.txt"
SCOPES = ['https://www.googleapis.com/auth/calendar']

class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, master, service, summary, start_iso, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Apstiprināt notikumu")
        self.geometry("400x420")
        self.service, self.summary, self.start_iso = service, summary, start_iso
        self.result = None
        self.attributes("-topmost", True)
        self.grab_set()

        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(expand=True, fill="both", padx=20, pady=20)
        ctk.CTkLabel(f, text="Atrasts jauns notikums", font=("Roboto Medium", 18)).pack(pady=(0, 15))
        
        inf = ctk.CTkFrame(f, corner_radius=10)
        inf.pack(fill="x", pady=10)
        ctk.CTkLabel(inf, text=summary, font=("Arial", 14, "bold"), wraplength=340).pack(pady=(15, 5))
        
        try:
            st_dt = datetime.datetime.fromisoformat(start_iso.split('+')[0].replace('Z', ''))
            ctk.CTkLabel(inf, text=f"Sākums: {st_dt.strftime('%d.%m.%Y %H:%M')}", font=("Arial", 12)).pack(pady=(5, 15))
        except:
            ctk.CTkLabel(inf, text=f"Sākums: {start_iso}", font=("Arial", 12)).pack(pady=(5, 15))

        self.conf_lbl = ctk.CTkLabel(f, text="Pārbauda kalendāru...", text_color="#E67E22", font=("Arial", 11, "bold"))
        self.conf_lbl.pack(pady=5)

        bf = ctk.CTkFrame(f, fg_color="transparent")
        bf.pack(pady=(20, 0))
        ctk.CTkButton(bf, text="Pievienot", fg_color="#2ecc71", width=100, command=self.on_yes).pack(side="left", padx=10)
        ctk.CTkButton(bf, text="Atmest", fg_color="#e74c3c", width=100, command=self.on_no).pack(side="left", padx=10)
        self.check_conflicts()

    def check_conflicts(self):
        try:
            res = self.service.events().list(calendarId='primary', timeMin=self.start_iso, 
                                           timeMax=self.start_iso[:10]+"T23:59:59Z", singleEvents=True).execute()
            if res.get('items'): self.conf_lbl.configure(text=f"⚠️ Konflikts ar: {res.get('items')[0].get('summary')}")
            else: self.conf_lbl.configure(text="✅ Laiks ir brīvs")
        except: self.conf_lbl.configure(text="Nevarēja pārbaudīt konfliktus")

    def on_yes(self): self.result = True; self.destroy()
    def on_no(self): self.result = False; self.destroy()

class CalendarApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Calendar Agent v5.2.5"); self.geometry("500x600")
        self.settings = self.load_settings()
        self.processed_emails = self.load_ids()
        self.running = False
        
        s_f = ctk.CTkFrame(self, corner_radius=15)
        s_f.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(s_f, text="Claude API Key:").pack(anchor="w", padx=25, pady=(10,0))
        self.ai_e = ctk.CTkEntry(s_f, show="*", width=350)
        self.ai_e.insert(0, self.settings.get("ai_key", "")); self.ai_e.pack(pady=5)

        ctk.CTkLabel(s_f, text="Inbox.lv E-pasts:").pack(anchor="w", padx=25)
        self.em_e = ctk.CTkEntry(s_f, width=350)
        self.em_e.insert(0, self.settings.get("email", "")); self.em_e.pack(pady=5)

        ctk.CTkLabel(s_f, text="App Parole:").pack(anchor="w", padx=25)
        self.pw_e = ctk.CTkEntry(s_f, show="*", width=350)
        self.pw_e.insert(0, self.settings.get("password", "")); self.pw_e.pack(pady=5)

        self.btn = ctk.CTkButton(self, text="SĀKT AI AĢENTU", fg_color="#2ecc71", height=45, command=self.start_sync)
        self.btn.pack(pady=10, padx=20, fill="x")

        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.log_box.pack(pady=10, padx=20, fill="both", expand=True)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
        return {"email":"", "password":"", "ai_key":""}

    def load_ids(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f: return set(line.strip() for line in f)
        return set()

    def save_id(self, m_id):
        self.processed_emails.add(m_id)
        with open(DB_FILE, "a") as f: f.write(f"{m_id}\n")

    def log(self, text, clear=False):
        if clear: self.log_box.delete("1.0", "end")
        self.log_box.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {text}\n")
        self.log_box.see("end")

    def start_sync(self):
        if not self.running:
            self.running = True; self.btn.configure(text="AĢENTS STRĀDĀ...", state="disabled")
            threading.Thread(target=self.main_loop, daemon=True).start()

    def main_loop(self):
        try:
            ai_key = self.ai_e.get(); email_u = self.em_e.get(); pwd = self.pw_e.get()
            with open(SETTINGS_FILE, "w") as f: json.dump({"email":email_u, "password":pwd, "ai_key":ai_key}, f)
            
            client = anthropic.Anthropic(api_key=ai_key)
            creds = None
            if os.path.exists('token.json'): creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                with open('token.json', 'w') as t: t.write(creds.to_json())
            service = build('calendar', 'v3', credentials=creds)

            mail = imaplib.IMAP4_SSL("mail.inbox.lv"); mail.login(email_u, pwd)
            self.log("🚀 Pieslēgts Inbox.lv")

            while self.running:
                mail.select("INBOX")
                _, data = mail.search(None, 'UNSEEN')
                ids = data[0].split()
                self.log(f"Meklēju jaunus e-pastus... (Atrasti: {len(ids)})", clear=True)
                
                for m_id in ids[-5:]:
                    m_id_s = m_id.decode()
                    if m_id_s in self.processed_emails: continue
                    
                    _, msg_data = mail.fetch(m_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    event_data = None
                    # 1. MEKLĒJAM ICS PIELIKUMU
                    for part in msg.walk():
                        if part.get_content_type() in ['text/calendar', 'application/ics']:
                            try:
                                ics_data = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                c = Calendar(ics_data)
                                e = list(c.events)[0]
                                event_data = {'summary': e.name, 'start': e.begin.isoformat()}
                                self.log(f"📎 Atrasts ICS pielikums: {e.name}")
                            except: pass

                    # 2. JA NAV PIELIKUMA, IZMANTOJAM AI ANALĪZI
                    if not event_data:
                        body = ""
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain":
                                body = p.get_payload(decode=True).decode('utf-8', 'ignore'); break
                        
                        if len(body) > 10:
                            self.log(f"🤖 AI analizē tekstu ID: {m_id_s}")
                            prompt = f"Extract meeting from: '{body[:1000]}'. Format: ISO 8601. Return ONLY JSON {{\"summary\": \"Title\", \"start\": \"2026-03-25T15:00:00\"}}"
                            resp = client.messages.create(
                                model="claude-3-haiku-20240307", max_tokens=200, system="JSON only.", 
                                messages=[{"role": "user", "content": prompt}]
                            )
                            match = re.search(r'\{.*\}', resp.content[0].text, re.DOTALL)
                            if match:
                                event_data = json.loads(match.group(0))

                    # 3. APSTRĀDĀJAM ATRADUMU
                    if event_data and 'start' in event_data:
                        if '+' not in event_data['start'] and 'Z' not in event_data['start']: 
                            event_data['start'] += "+02:00"
                        
                        self.save_id(m_id_s) # Atzīmējam kā apstrādātu uzreiz
                        
                        done = threading.Event()
                        def ask():
                            d = ConfirmationDialog(self, service, event_data['summary'], event_data['start'])
                            self.wait_window(d)
                            if d.result:
                                st = datetime.datetime.fromisoformat(event_data['start'].replace('Z',''))
                                en = (st + datetime.timedelta(hours=1)).isoformat()
                                service.events().insert(calendarId='primary', body={
                                    'summary': event_data['summary'], 'start': {'dateTime': event_data['start']}, 'end': {'dateTime': en}
                                }).execute()
                                self.log(f"✅ Pievienots: {event_data['summary']}")
                            else:
                                self.log(f"⏭️ Atmests: {event_data['summary']}")
                            done.set()
                        self.after(0, ask); done.wait()
                    else:
                        # Ja nekas netika atrasts, vienalga atzīmējam kā apstrādātu
                        self.save_id(m_id_s)
                
                time.sleep(30)
        except Exception as e: 
            self.log(f"❌ Kļūda: {e}")
            self.running = False; self.btn.configure(text="Mēģināt vēlreiz", state="normal")

if __name__ == "__main__":
    app = CalendarApp(); app.mainloop()
