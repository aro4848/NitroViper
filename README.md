# NitroViper

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Discord](https://img.shields.io/badge/Discord-aro22-7289DA)](https://discord.com/users/aro22)
[![GitHub Stars](https://img.shields.io/github/stars/aro4848/NitroViper?style=flat-square)](https://github.com/aro4848/NitroViper)

discord nitro sniper. strike fast, redeem faster.

most snipers out there rely on bloated libraries like discord.py that load giant guild caches and waste 200ms before they even see the message. NitroViper connects straight to the raw discord gateway websocket (v9) and fires claims over an already pre-warmed keep-alive http pool before other bots even process the event.

```text
                    ***********####
                   ******************##
                   #***************######
                         *****+===+*#######
            *** ************-.......:+######
            ##  #######****..:------..=#####
                  ****####-.:--------.:#####
                  ########=.:--------.:#####
                     #####*:.:-----:.*#####
                      ######+::...::=######
                       ###################               [skibidi]- made by skibidi aro https://github.com/aro4848
                        #################                 [discord]: https://discord.com/users/aro22 on discord
                           ############                   [Engine: NitroViper Ultra-Fast]
```

### how it works

- **raw websocket gateway**: listens directly on `wss://gateway.discord.gg/?v=9&encoding=json` with sub-microsecond string checks before regex.
- **pre-warmed tls pool**: keeps an open tcp connection hot to discord so claims dispatch in <1ms without handshake delay.
- **zero config token grabber**: decrypts active tokens straight out of your local discord desktop app (dpapi + leveldb) on windows. no need to paste tokens manually.
- **origin spoofing**: passes the real channel_id and authentic desktop client headers (`X-Super-Properties`) so discord doesn't auto-reject claims with 400.
- **multi-watcher**: listen across multiple accounts and hundreds of servers at the same time.
- **async webhooks**: webhook alerts run in background tasks so notifications never slow down the claiming path.

### setup

```bash
git clone https://github.com/aro4848/NitroViper.git
cd NitroViper
pip install aiohttp pywin32 cryptography
```

### run

```bash
python NitroViper.py
```

if discord desktop is running or logged in on your pc, it will automatically find your session and start watching all your servers.

if you want to use multiple accounts or add a webhook, edit `config.json`:

```json
{
    "webhook_url": "YOUR_DISCORD_WEBHOOK_URL",
    "github_repo_url": "https://github.com/aro4848/NitroViper",
    "watcher_tokens": [
        "SECONDARY_ACCOUNT_TOKEN"
    ],
    "redeemer_token": "MAIN_ACCOUNT_TOKEN"
}
```

### disclaimer

I (as aro4848) dont give a fuck if something happens to ur account. selfbots violate discord TOS so dont complain if you get banned. if you need help msg me on discord: **aro22**

![nitrosuccess](https://github.com/user-attachments/assets/dfde9813-e584-414e-9867-a1745874bb72)
