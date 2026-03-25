# 📅 Kalendāra Aģents v5.2

Gudrs palīgs, kas automātiski skenē Tavus e-pastus (Inbox.lv, Gmail, Outlook) un, izmantojot **Claude AI (Anthropic)**, atpazīst pasākumus, lai pievienotu tos Tavam Google kalendāram.

## ✨ Galvenās iespējas
- **AI Analīze:** Ja e-pastam nav pievienots kalendāra fails (.ics), aģents nolasa tekstu un saprot, kad un kas notiek.
- **Konfliktu pārbaude:** Pirms pasākuma pievienošanas aģents pārbauda, vai tajā laikā kalendārs jau nav aizņemts.
- **Drošība:** API atslēgas un paroles netiek glabātas kodā, bet gan lokālā lietotāja failā.
- **Viedā atmiņa:** Programma atceras apstrādātos e-pastus, lai netērētu AI kredītus dubultā.

## 🚀 Kā palaist?
1. Lejupielādē `cl05.py`.
2. Mapē jābūt Tavam Google Cloud `credentials.json` failam.
3. Instalē nepieciešamās bibliotēkas:
   ```bash
   pip install customtkinter anthropic ics google-api-python-client google-auth-oauthlib