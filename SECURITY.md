# Security Policy

## ⚠️ Telegram Credentials & Session Security Notice

This application uses the official Telegram MTProto client protocol ([Telethon](https://github.com/LonamiWebs/Telethon)) to communicate directly with Telegram's Data Centers.

### 🚨 Critical Security Rules:
1. **Never commit or share `.env`**:
   - Your `.env` contains your `TG_API_ID` and `TG_API_HASH`.
2. **Never commit or share `*.session` files**:
   - `tg_session.session` contains the cryptographic authentication key granted to your Telegram account by Telegram's servers. Anyone with this file has full access to your Telegram account!
3. **Protected by `.gitignore`**:
   - Both `.env` and `*.session` are ignored by default in this repository. Always double-check `git status` before pushing commits to public repositories.

---

## Reporting a Vulnerability

If you discover a potential security vulnerability in Telegram Video Downloader, please report it privately:

1. **Do NOT open a public GitHub issue.**
2. Send an email to the repository maintainer or open a private GitHub Security Advisory.
3. Include detailed steps, screenshots, or proof-of-concept to help reproduce and resolve the issue promptly.

We take security reports seriously and will acknowledge receipt and work on a fix as quickly as possible.
