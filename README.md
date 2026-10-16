# **NitroViper**

> Strike Fast. Redeem Faster.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-aro22-7289DA)](https://discord.com/users/aro22)
[![GitHub Stars](https://img.shields.io/github/stars/aro4848/NitroViper?style=flat-square)](https://github.com/aro4848/NitroViper)

Ultra high-speed Discord Nitro sniper engineered with raw asynchronous WebSockets and pre-warmed HTTP/2 keep-alive pools.

---

### 🚀 Key Features

- ⚡ **Raw Gateway Engine (v9)**: Zero-overhead WebSocket message stream with direct opcode dispatch (<1ms processing latency).
- 🏎️ **Pre-warmed Keep-Alive HTTP Pool**: Maintains hot TLS sockets to `discord.com` to eliminate TCP/TLS handshake latency upon code redemption.
- 🔑 **Automatic Windows DPAPI Token Discovery**: Auto-detects and decrypts active session tokens directly from local Discord Desktop installations.
- 👥 **Multi-Account Watcher Aggregation**: Concurrently monitor hundreds of servers across multiple watcher accounts.
- 🛡️ **Context-Aware Redemption**: Dynamically injects origin `channel_id` and authentic desktop client headers (`X-Super-Properties`) to bypass bot heuristics.
- 🔔 **Non-Blocking Webhooks**: Webhook notifications run in isolated background tasks and never delay the critical claiming path.

---

### 📦 Installation

```bash
git clone https://github.com/aro4848/NitroViper.git
cd NitroViper
pip install aiohttp pywin32 cryptography
```

---

### ⚙️ Quick Start

1. Run the script:
   ```bash
   python NitroViper.py
   ```
2. **Zero-Configuration Mode**: If running on Windows with Discord Desktop logged in, NitroViper will automatically discover and use your active session tokens.
3. **Manual Configuration** (Optional): Edit `config.json` to customize your webhook URL or add secondary watcher tokens:
   ```json
   {
       "webhook_url": "YOUR_WEBHOOK_URL",
       "github_repo_url": "https://github.com/aro4848/NitroViper",
       "watcher_tokens": [
           "SECONDARY_WATCHER_TOKEN_HERE"
       ],
       "redeemer_token": "MAIN_ACCOUNT_TOKEN_HERE"
   }
   ```

---

### ⚠️ Disclaimer

I (as aro4848) dont give a fuck if something happens to ur account. since this will violate the **TOS** of **Discord**. so dont complain if you got banned. <ins>Msg me if u needed any help on discord.</ins>

![nitrosuccess](https://github.com/user-attachments/assets/dfde9813-e584-414e-9867-a1745874bb72)
