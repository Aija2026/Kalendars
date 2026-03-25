# 📅 AI Calendar Agent / Kalendāra Aģents v5.2

An intelligent Python-based agent that monitors your Inbox for event invitations and automatically synchronizes them with Google Calendar using Claude-3 AI.

Gudrs palīgs, kas automātiski skenē e-pastus (Inbox.lv, Gmail, Outlook) un, izmantojot Claude AI, atpazīst pasākumus, lai pievienotu tos Google kalendāram.

---

### ✨ Features / Galvenās iespējas

* **Smart AI Extraction:** Uses Claude-3 to parse event details from plain text emails—no ICS required.
    *(AI Analīze: Ja e-pastam nav .ics faila, aģents nolasa tekstu un saprot pasākuma laiku un būtību.)*
* **Conflict Detection:** Automatically checks your Google Calendar for existing events before adding new ones.
    *(Konfliktu pārbaude: Pirms pievienošanas pārbauda, vai laiks kalendārā jau nav aizņemts.)*
* **Privacy & Security:** Local settings storage and secure credential handling. No passwords in code.
    *(Drošība: API atslēgas un paroles tiek glabātas lokālā lietotāja failā, nevis kodā.)*
* **Smart Memory:** Remembers processed emails to avoid duplicate AI processing.
    *(Viedā atmiņa: Programma atceras apstrādātos e-pastus, lai netērētu AI resursus dubultā.)*

---

### 🛠️ Tech Stack / Tehnoloģijas

* **Language:** Python (CustomTkinter GUI)
* **AI Engine:** Anthropic API (Claude-3 Haiku)
* **Integration:** Google Calendar API, IMAP

---

### 🚀 How to Run / Kā palaist?

1.  **Download** `cl05.py`.
2.  Ensure your Google Cloud `credentials.json` is in the same folder.
3.  **Install requirements:**
    ```bash
    pip install customtkinter anthropic ics google-api-python-client google-auth-oauthlib
    ```
4.  **Run the script:**
    ```bash
    python cl05.py
    ```

---

### 💡 Personal Use Case / Kāpēc šis ir noderīgi?
My primary email for job searching is **Inbox.lv**, while personal events are on **Gmail**. This agent unifies everything into one calendar to prevent scheduling conflicts.

*(Mans galvenais e-pasts darba meklēšanai ir Inbox.lv, bet draugiem — Gmail. Šis aģents apvieno abus, lai pasākumi nepārklātos.)*
