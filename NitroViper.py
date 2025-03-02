

import sys
import subprocess
import importlib
import os

# List of required modules
REQUIRED_MODULES = ["discord", "aiohttp", "ctypes", "json", "re", "asyncio", "datetime"]

def clear_terminal():
    # I love reina.
    os.system('cls' if os.name == 'nt' else 'clear')

def ensure_dependencies():
    # she is the best
    missing_modules = []
    for module_name in REQUIRED_MODULES:
        try:
            # try to import SKIBIDI
            importlib.import_module(module_name)
        except ImportError:
            missing_modules.append(module_name)

    if missing_modules:
        print("[⚠️] Missing modules detected. Installing...")
        for module_name in missing_modules:
            print(f"[⏳] Installing '{module_name}'...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            print(f"[✅] Module '{module_name}' installed successfully.")
        
        # clear this mess please.
        clear_terminal()
        print("[✅] All dependencies installed and terminal cleared.\n")

# im gonna fucking kill my self.





import discord
import re
import aiohttp
import asyncio
import sys
import ctypes
import json
from datetime import datetime, UTC
import time
banner_printed = False


try:
    with open("config.json", "r") as config_file:
        CONFIG = json.load(config_file)
except FileNotFoundError:
    print("[❌] config.json not found")
    time.sleep(5)
    sys.exit(1)

WEBHOOK_URL = CONFIG.get("webhook_url", "")
GITHUB_REPO_URL = CONFIG.get("github_repo_url", "")
WATCHER_TOKENS = CONFIG.get("watcher_tokens", [])
REDEEMER_TOKEN = CONFIG.get("redeemer_token", "")

WATCHER_TOKENS = [token for token in WATCHER_TOKENS if token.strip()]
if not REDEEMER_TOKEN.strip():
    print("[⚠️] Where the fuck is the redeemer token at?? ")
    time.sleep(5)
    #barack obama 
    sys.exit(1)

code_queue = asyncio.Queue()

class ArtAttackClient(discord.Client):
    def __init__(self, role, token, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.role = role
        self.token = token
        self.sniped = 0
        self.cache = set()
        self.session = None
        self.webhook_enabled = bool(WEBHOOK_URL)
        self.headers = {'Authorization': token}

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

    async def send_webhook_notification(self, code, status, author_name, channel_name, guild_name=None):
        if not self.webhook_enabled or not self.session:
            return

        color_map = {
            "SUCCESS": 0xFF69B4,
            "ALREADY_REDEEMED": 0xFEE75C,
            "FAILED": 0xED4245,
        }
        color = color_map.get(status, 0x5865F2)

        embed = {
            "title": f"💎 Nitro Code Attempt: `{code}`",
            "description": f"**Status**: {status}",
            "color": color,
            "timestamp": datetime.now(UTC).isoformat(),
            "fields": [
                {"name": "Author", "value": author_name, "inline": True},
                {"name": "Channel", "value": channel_name, "inline": True},
            ],
        }

        if guild_name:
            embed["fields"].append({"name": "Server", "value": guild_name, "inline": True})

        components = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Rate Me",
                        "url": GITHUB_REPO_URL,
                    }
                ]
            }
        ]

        payload = {
            "embeds": [embed],
            "components": components,
        }

        try:
            async with self.session.post(WEBHOOK_URL, json=payload) as response:
                pass
        except Exception:
            pass

    async def instant_redeem(self, code):
        if not self.session:
            return {"message": "Session not initialized!"}
        
        try:
            async with self.session.post(
                f'https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem',
                headers=self.headers,
                json={'channel_id': None},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return await response.json()
        except Exception:
            return {"message": "Failed to redeem code"}

    async def on_message(self, message):
        if not self.session:
            return

        pattern = r'(?:discord\.gift/|discord\.com/gifts/|discordapp.com/gifts/)([a-zA-Z0-9]{16,24})'
        matches = re.findall(pattern, message.content, re.IGNORECASE)
        
        for code in matches:
            if code in self.cache:
                continue
            self.cache.add(code)

            if self.role == "watcher":
                await code_queue.put((code, message.author.name, message.channel.name, message.guild.name if message.guild else None))
            elif self.role == "redeemer":
                result = await self.instant_redeem(code)
                status = "FAILED"
                
                if 'subscription_plan' in result:
                    status = "SUCCESS"
                    self.sniped += 1
                elif 'already been redeemed' in result.get('message', ''):
                    status = "ALREADY_REDEEMED"
                
                await self.send_webhook_notification(
                    code=code,
                    status=status,
                    author_name=message.author.name,
                    channel_name=message.channel.name,
                    guild_name=message.guild.name if message.guild else None,
                )

    async def on_ready(self):
        global banner_printed

        self.session = aiohttp.ClientSession()

        if not banner_printed:
            banner_color = "\033[38;2;70;84;117m"
            github_color = "\033[38;2;27;28;33m"
            discord_color = "\033[38;2;84;97;235m"
            logged_in_color = "\033[38;2;212;135;190m"
            white_color = "\033[38;2;255;255;255m"
            reset_color = "\033[0m"

            total_watchers = len(WATCHER_TOKENS)
            total_servers = sum(len(client.guilds) for client in watchers)

            print(f"\n\n\n{banner_color}"
                  
                  f"                    ***********####                                                     \n"
                  f"                   ******************##     \n"
                  f"                   #***************######                \n"
                  f"                         *****+===+*####### \n"
                  f"            *** ************-{white_color}.......{banner_color}:+######\n"
                  f"            ##  #######****{white_color}..:------..{banner_color}=#####\n"
                  f"                  ****####-{white_color}.:--------.{banner_color}:#####\n"
                  f"                  ########={white_color}.:--------.{banner_color}:#####\n"
                  f"                     #####*{white_color}:.:-----:.{banner_color}*#####\n"
                  f"                      ######+{white_color}::...::{banner_color}=######              \n"
                  f"                       ###################               {reset_color}{github_color}[skibidi]- made by skibidi aro https://github.com/aro4848{reset_color}\n"
                  f"{banner_color}                        #################                 {reset_color}{discord_color}[discord]: https://discord.com/users/aro22 on discord{reset_color}\n"
                  f"{banner_color}                           ############                   {reset_color}{logged_in_color}[Logged in {total_watchers} watchers | Watching {total_servers} servers]{reset_color}")

            banner_printed = True

        asyncio.create_task(self.update_console_title())

    async def update_console_title(self):
        while not self.is_closed():
            try:
                latency = round(self.latency * 1000)
                latency_status = "Excellent" if latency < 50 else "Good" if latency < 150 else "Fair" if latency < 300 else "Poor"
                ctypes.windll.kernel32.SetConsoleTitleW(f"[ArtAttack] Latency: {latency}ms ({latency_status}) | Sniped: {self.sniped}")
            except Exception:
                pass
            await asyncio.sleep(5)

watchers = [ArtAttackClient(role="watcher", token=token) for token in WATCHER_TOKENS]
redeemer = ArtAttackClient(role="redeemer", token=REDEEMER_TOKEN) if REDEEMER_TOKEN.strip() else None

async def main():
    if not WATCHER_TOKENS:
        print("[❌] No valid watcher tokens found. Exiting...")
        time.sleep(5)
        sys.exit(1)

    watcher_tasks = [asyncio.create_task(watcher.start(watcher_token)) for watcher, watcher_token in zip(watchers, WATCHER_TOKENS)]
    
    if redeemer:
        redeemer_task = asyncio.create_task(redeemer.start(REDEEMER_TOKEN))
    
    while True:
        code, author, channel, guild = await code_queue.get()
        if redeemer:
            result = await redeemer.instant_redeem(code)
            status = "FAILED"
            
            if 'subscription_plan' in result:
                status = "SUCCESS"
                redeemer.sniped += 1
            elif 'already been redeemed' in result.get('message', ''):
                status = "ALREADY_REDEEMED"
            
            await redeemer.send_webhook_notification(
                code=code,
                status=status,
                author_name=author,
                channel_name=channel,
                guild_name=guild,
            )

asyncio.run(main())
ensure_dependencies()


#بسمالله الرحمن الرحيم.
#In the name of Allah, the Most Gracious, the Most Merciful
#58:15 Allah has prepared for them a severe punishment. Indeed, it was evil that they were doing.

#3/2/2025 i made this.
#3/2/2025 i made this.
#3/2/2025 i made this.
#6/25/2024 you made me go insane..
# i dont fucking know why and how i made this.
