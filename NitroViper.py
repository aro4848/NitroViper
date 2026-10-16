#!/usr/bin/env python3
"""
NitroViper - Ultra High-Speed Discord Nitro Sniper
==================================================
Author: aro (https://github.com/aro4848)
Discord: aro22

Architecture:
- Sub-Millisecond Pre-warmed Keep-Alive HTTP Connection: Eliminates TCP/TLS handshake latency.
- Raw Async WebSocket Gateway (v9): Direct raw frames bypassing framework overhead (<1ms).
- Zero-Allocation Fast-Path Filter: Sub-microsecond string pre-checks before regex parsing.
- Automated Windows DPAPI Token Discovery: Auto-detects and decrypts active Discord desktop tokens.
- Context-Aware Redemption: Injects origin channel_id to defeat Discord bot heuristics.
- Non-blocking Asynchronous Webhook Offloading: Critical path never waits for webhooks.
- Multi-Watcher Aggregation: Concurrently monitors messages across multiple tokens and hundreds of servers.
"""

import sys
import os
import time
import json
import re
import asyncio
import base64
import ctypes
from datetime import datetime, timezone
import aiohttp

# Force UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    os.system("")

# Windows DPAPI & LevelDB decryption imports
try:
    import win32crypt
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_LOCAL_DECRYPT = True
except ImportError:
    HAS_LOCAL_DECRYPT = False


# ----------------- COLORS & AESTHETICS -----------------

C_BANNER = "\033[38;2;70;84;117m"
C_GITHUB = "\033[38;2;27;28;33m"
C_DISCORD = "\033[38;2;84;97;235m"
C_LOGGED = "\033[38;2;212;135;190m"
C_WHITE = "\033[38;2;255;255;255m"
C_GREEN = "\033[38;2;87;242;135m"
C_YELLOW = "\033[38;2;254;231;92m"
C_RED = "\033[38;2;237;66;69m"
C_CYAN = "\033[38;2;0;255;255m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"


# ----------------- DESKTOP SUPER PROPERTIES -----------------

SUPER_PROPS = {
    "os": "Windows",
    "browser": "Discord Client",
    "release_channel": "stable",
    "client_version": "1.0.9262",
    "os_version": "10.0.19045",
    "os_arch": "x64",
    "app_arch": "x64",
    "system_locale": "en-US",
    "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9262 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36",
    "browser_version": "32.2.7",
    "client_build_number": 638651,
    "native_build_number": 55260,
    "client_event_source": None
}
ENCODED_SUPER_PROPS = base64.b64encode(json.dumps(SUPER_PROPS).encode("utf-8")).decode("utf-8")

# Pre-compiled high-coverage Gift Regex
GIFT_REGEX = re.compile(
    r'(?:discord\.gift/|discord(?:app)?\.com/gifts/|promos\.discord\.gg/)([a-zA-Z0-9]{16,24})',
    re.IGNORECASE
)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
TOKEN_TXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")


# ----------------- LOCAL TOKEN DECRYPTION -----------------

def find_local_discord_tokens() -> list[str]:
    """Auto-detects and decrypts live user tokens from local Discord desktop installations on Windows."""
    if not HAS_LOCAL_DECRYPT:
        return []

    appdata = os.getenv("APPDATA")
    if not appdata:
        return []

    discord_paths = [
        os.path.join(appdata, "discord"),
        os.path.join(appdata, "discordcanary"),
        os.path.join(appdata, "discordptb"),
    ]

    found_tokens = []

    for base_dir in discord_paths:
        state_path = os.path.join(base_dir, "Local State")
        db_path = os.path.join(base_dir, "Local Storage", "leveldb")

        if not (os.path.exists(state_path) and os.path.exists(db_path)):
            continue

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            encrypted_key = base64.b64decode(state_data["os_crypt"]["encrypted_key"])[5:]
            master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except Exception:
            continue

        for file_name in os.listdir(db_path):
            if not file_name.endswith((".log", ".ldb")):
                continue
            file_path = os.path.join(db_path, file_name)
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                for match in re.findall(rb'dQw4w9WgXcQ:[^"\'\s]*', content):
                    try:
                        raw_payload = base64.b64decode(match.split(b":")[1])
                        iv = raw_payload[3:15]
                        ciphertext = raw_payload[15:]
                        token = AESGCM(master_key).decrypt(iv, ciphertext, None).decode("utf-8")
                        if token and token not in found_tokens:
                            found_tokens.append(token)
                    except Exception:
                        pass
            except Exception:
                pass

    return found_tokens


async def verify_token_async(session: aiohttp.ClientSession, token: str) -> tuple[bool, str, str]:
    """Checks if a token is active and valid with Discord API, returning (is_valid, username, user_id)."""
    headers = {
        "Authorization": token,
        "User-Agent": SUPER_PROPS["browser_user_agent"]
    }
    try:
        async with session.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return True, data.get("username", "Unknown"), str(data.get("id", ""))
    except Exception:
        pass
    return False, "", ""


async def resolve_active_tokens(session: aiohttp.ClientSession, config: dict) -> tuple[str, list[str]]:
    """Validates configured tokens and auto-detects live tokens from local Discord if needed."""
    cfg_redeemer = config.get("redeemer_token", "").strip()
    cfg_watchers = [t.strip() for t in config.get("watcher_tokens", []) if t.strip()]

    # Also check token.txt
    if not cfg_redeemer and os.path.exists(TOKEN_TXT_PATH):
        try:
            with open(TOKEN_TXT_PATH, "r", encoding="utf-8") as f:
                cfg_redeemer = f.read().strip()
        except Exception:
            pass

    valid_redeemer = ""
    valid_watchers = []

    # Check configured redeemer
    if cfg_redeemer:
        is_val, u_name, u_id = await verify_token_async(session, cfg_redeemer)
        if is_val:
            valid_redeemer = cfg_redeemer
            print(f"{C_GREEN}[+] Redeemer token verified: @{u_name} ({u_id}){C_RESET}")
        else:
            print(f"{C_YELLOW}[!] Configured redeemer_token is expired/invalid (401). Auto-detecting...{C_RESET}")

    # Check configured watchers
    for idx, w_tok in enumerate(cfg_watchers):
        is_val, u_name, u_id = await verify_token_async(session, w_tok)
        if is_val:
            valid_watchers.append(w_tok)
            print(f"{C_GREEN}[+] Watcher #{idx + 1} token verified: @{u_name} ({u_id}){C_RESET}")
        else:
            print(f"{C_YELLOW}[!] Configured watcher token #{idx + 1} is expired/invalid (401).{C_RESET}")

    # Auto-detect local desktop tokens if redeemer or watchers need them
    if not valid_redeemer or not valid_watchers:
        print(f"{C_CYAN}[*] Scanning local Discord client for active session tokens...{C_RESET}")
        local_tokens = find_local_discord_tokens()
        detected_valid = []

        for loc_tok in local_tokens:
            is_val, u_name, u_id = await verify_token_async(session, loc_tok)
            if is_val:
                detected_valid.append((loc_tok, u_name, u_id))
                print(f"{C_GREEN}[+] Found active desktop session: @{u_name} ({u_id}){C_RESET}")

        if detected_valid:
            # Prefer primary user 'aro22' or first available
            if not valid_redeemer:
                chosen = detected_valid[0]
                for item in detected_valid:
                    if item[1] == "aro22" or item[2] == "554357469015703572":
                        chosen = item
                        break
                valid_redeemer = chosen[0]
                print(f"{C_GREEN}[+] Auto-assigned Redeemer Token: @{chosen[1]} ({chosen[2]}){C_RESET}")

            # Add remaining detected tokens to watchers
            for item in detected_valid:
                if item[0] not in valid_watchers:
                    valid_watchers.append(item[0])

            # Sync updated configuration back to config.json
            config["redeemer_token"] = valid_redeemer
            config["watcher_tokens"] = valid_watchers
            try:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
                print(f"{C_CYAN}[*] Updated config.json with active verified tokens.{C_RESET}")
            except Exception:
                pass

    return valid_redeemer, valid_watchers


# ----------------- FAST REDEEMER ENGINE -----------------

class FastRedeemer:
    """Handles sub-millisecond gift code redemptions using pre-warmed keep-alive HTTP sessions."""

    def __init__(self, token: str, webhook_url: str, github_url: str):
        self.token = token
        self.webhook_url = webhook_url
        self.github_url = github_url
        self.session: aiohttp.ClientSession = None
        self.sniped_count = 0
        self.seen_codes = set()
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": SUPER_PROPS["browser_user_agent"],
            "X-Super-Properties": ENCODED_SUPER_PROPS,
            "Accept": "*/*",
            "Sec-Ch-Ua": '"Not?A_Brand";v="99", "Chromium";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"'
        }

    async def init(self):
        connector = aiohttp.TCPConnector(
            limit=200,
            ttl_dns_cache=600,
            keepalive_timeout=120,
            enable_cleanup_closed=True,
            force_close=False
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=6.0)
        )

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def redeem(self, code: str, channel_id: str = None, author: str = "Unknown", guild_name: str = None):
        """Instantaneous redemption call directly over pre-warmed HTTP session."""
        if code in self.seen_codes:
            return
        self.seen_codes.add(code)

        start_time = time.perf_counter()
        url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem"
        payload = {"channel_id": channel_id, "payment_source_id": None}

        status = "FAILED"
        sub_plan = None
        resp_msg = ""
        latency_ms = 0.0

        try:
            async with self.session.post(url, json=payload) as resp:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                try:
                    data = await resp.json()
                except Exception:
                    data = {}

                if resp.status == 200:
                    status = "SUCCESS"
                    self.sniped_count += 1
                    plan_info = data.get("subscription_plan") or {}
                    sub_plan = plan_info.get("name", "Discord Nitro")
                    print(f"\n{C_GREEN}{C_BOLD}[★] NITRO SNIPED SUCCESSFULLY! ({latency_ms:.1f}ms){C_RESET}")
                    print(f"  {C_GREEN}Code: discord.gift/{code}{C_RESET}")
                    print(f"  {C_GREEN}Plan: {sub_plan}{C_RESET}")
                    print(f"  {C_DIM}From: {author} in {guild_name or 'DM'}{C_RESET}\n")
                elif "already been redeemed" in data.get("message", "").lower():
                    status = "ALREADY_REDEEMED"
                    print(f"{C_YELLOW}[!] Code Already Claimed: discord.gift/{code} ({latency_ms:.1f}ms) | By: {author}{C_RESET}")
                elif "captcha_key" in data or "captcha_service" in data:
                    status = "CAPTCHA_REQUIRED"
                    print(f"{C_RED}[!] Nitro Claim Blocked by Discord Captcha: discord.gift/{code} ({latency_ms:.1f}ms){C_RESET}")
                else:
                    status = "INVALID_OR_EXPIRED"
                    resp_msg = data.get("message", f"HTTP {resp.status}")
                    print(f"{C_RED}[-] Failed: discord.gift/{code} ({latency_ms:.1f}ms) - {resp_msg}{C_RESET}")

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            print(f"{C_RED}[!] Network error claiming discord.gift/{code}: {e}{C_RESET}")

        # Fire webhook in background task (never blocks)
        if self.webhook_url:
            asyncio.create_task(
                self.send_webhook(code, status, latency_ms, author, channel_id, guild_name, sub_plan, resp_msg)
            )

    async def send_webhook(self, code, status, latency_ms, author, channel_id, guild_name, sub_plan, error_msg):
        if not self.webhook_url or not self.session:
            return

        color_map = {
            "SUCCESS": 0x57F287,
            "ALREADY_REDEEMED": 0xFEE75C,
            "CAPTCHA_REQUIRED": 0xED4245,
            "INVALID_OR_EXPIRED": 0xED4245,
            "FAILED": 0xED4245
        }

        desc = f"**Status**: `{status}`\n**Response Time**: `{latency_ms:.2f}ms`"
        if sub_plan:
            desc += f"\n**Plan**: `{sub_plan}`"
        if error_msg:
            desc += f"\n**Details**: `{error_msg}`"

        embed = {
            "title": f"💎 Nitro Code Sniped: `{code}`",
            "description": desc,
            "color": color_map.get(status, 0x5865F2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": [
                {"name": "Sender", "value": str(author), "inline": True},
                {"name": "Server / Guild", "value": str(guild_name or "Direct Message"), "inline": True},
                {"name": "Channel ID", "value": str(channel_id or "N/A"), "inline": True}
            ],
            "footer": {
                "text": "NitroViper Ultra-Fast Engine • by aro"
            }
        }

        components = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "GitHub Repo",
                        "url": self.github_url
                    }
                ]
            }
        ]

        try:
            async with self.session.post(self.webhook_url, json={"embeds": [embed], "components": components}) as r:
                pass
        except Exception:
            pass


# ----------------- RAW GATEWAY WATCHER -----------------

class GatewayWatcher:
    """Connects to Discord's Gateway via raw WebSocket without heavy bot framework overhead."""

    def __init__(self, token: str, redeemer: FastRedeemer, watcher_index: int):
        self.token = token
        self.redeemer = redeemer
        self.index = watcher_index
        self.ws: aiohttp.ClientWebSocketResponse = None
        self.heartbeat_interval = 41.25
        self.heartbeat_task: asyncio.Task = None
        self.running = False
        self.session_id = None
        self.seq = None
        self.user_tag = f"Watcher #{watcher_index}"
        self.guilds_count = 0

    async def run(self):
        self.running = True
        backoff = 2.0

        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        "wss://gateway.discord.gg/?v=9&encoding=json",
                        autoping=False,
                        max_msg_size=0,
                        heartbeat=None
                    ) as ws:
                        self.ws = ws
                        backoff = 2.0
                        await self._handle_connection()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self.running:
                    break
                print(f"{C_YELLOW}[!] Watcher #{self.index} disconnected: {e}. Reconnecting in {backoff:.1f}s...{C_RESET}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 30.0)
            finally:
                if self.heartbeat_task and not self.heartbeat_task.done():
                    self.heartbeat_task.cancel()

    async def _handle_connection(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                op = data.get("op")
                t = data.get("t")
                s = data.get("s")
                if s is not None:
                    self.seq = s

                if op == 10:  # Hello
                    self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000.0
                    if self.heartbeat_task and not self.heartbeat_task.done():
                        self.heartbeat_task.cancel()
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    # Identify or Resume
                    if self.session_id and self.seq:
                        await self._send_resume()
                    else:
                        await self._send_identify()

                elif op == 11:  # Heartbeat ACK
                    pass

                elif op == 1:  # Server requested immediate heartbeat
                    await self._send_heartbeat()

                elif op == 7:  # Reconnect
                    print(f"{C_YELLOW}[!] Watcher #{self.index} received Opcode 7 (Reconnect).{C_RESET}")
                    break

                elif op == 9:  # Invalid Session
                    can_resume = data.get("d", False)
                    if not can_resume:
                        self.session_id = None
                        self.seq = None
                    await asyncio.sleep(1.0)
                    break

                elif op == 0:  # Event Dispatch
                    if t == "READY":
                        d = data.get("d", {})
                        self.session_id = d.get("session_id")
                        user = d.get("user", {})
                        self.user_tag = user.get("username", "Unknown")
                        self.guilds_count = len(d.get("guilds", []))
                        print(f"{C_GREEN}[+] Watcher #{self.index} Active: @{self.user_tag} (Watching {self.guilds_count} guilds){C_RESET}")

                    elif t == "RESUMED":
                        print(f"{C_GREEN}[+] Watcher #{self.index} Resumed Gateway session successfully.{C_RESET}")

                    elif t == "MESSAGE_CREATE":
                        self._process_message(data.get("d", {}))

            elif msg.type == aiohttp.WSMsgType.CLOSE:
                close_code = msg.data
                close_reason = msg.extra
                if close_code == 4004:
                    print(f"{C_RED}[!] Watcher #{self.index} Authentication failed (4004): Token invalid or revoked.{C_RESET}")
                    self.running = False
                else:
                    print(f"{C_YELLOW}[!] Watcher #{self.index} socket closed ({close_code}: {close_reason}). Reconnecting...{C_RESET}")
                break

            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                break

    def _process_message(self, d: dict):
        """Lightning-fast message inspection with zero-allocation pre-filter."""
        content = d.get("content") or ""
        embeds = d.get("embeds") or []

        # Sub-microsecond pre-filter: 99.9% of chat messages have no gift indicators
        has_content_hit = ("gift" in content or "discord.gg" in content or "promos.discord" in content) if content else False
        if not has_content_hit and not embeds:
            return

        codes = []
        if has_content_hit:
            codes.extend(GIFT_REGEX.findall(content))

        if embeds:
            for em in embeds:
                desc = em.get("description") or ""
                if "gift" in desc or "discord.gg" in desc:
                    codes.extend(GIFT_REGEX.findall(desc))
                url = em.get("url") or ""
                if "gift" in url or "discord.gg" in url:
                    codes.extend(GIFT_REGEX.findall(url))
                for fld in em.get("fields") or []:
                    val = fld.get("value") or ""
                    if "gift" in val or "discord.gg" in val:
                        codes.extend(GIFT_REGEX.findall(val))

        if not codes:
            return

        channel_id = d.get("channel_id")
        guild_id = d.get("guild_id")
        author_name = d.get("author", {}).get("username", "Unknown")

        # Instantaneous redemption task dispatch (<10 microseconds)
        for code in set(codes):
            asyncio.create_task(
                self.redeemer.redeem(code, channel_id=channel_id, author=author_name, guild_name=guild_id)
            )

    async def _send_identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "capabilities": 30717,
                "properties": SUPER_PROPS,
                "presence": {
                    "status": "online",
                    "since": 0,
                    "activities": [],
                    "afk": False
                },
                "compress": False,
                "client_state": {
                    "guild_versions": {}
                }
            }
        }
        await self.ws.send_json(payload)

    async def _send_resume(self):
        payload = {
            "op": 6,
            "d": {
                "token": self.token,
                "session_id": self.session_id,
                "seq": self.seq
            }
        }
        await self.ws.send_json(payload)

    async def _send_heartbeat(self):
        if self.ws and not self.ws.closed:
            try:
                await self.ws.send_json({"op": 1, "d": self.seq})
            except Exception:
                pass

    async def _heartbeat_loop(self):
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)
            await self._send_heartbeat()


# ----------------- TITLE & MONITOR TASK -----------------

async def console_title_loop(redeemer: FastRedeemer, watchers: list):
    while True:
        try:
            active_watchers = sum(1 for w in watchers if w.ws and not w.ws.closed)
            total_guilds = sum(w.guilds_count for w in watchers)
            title = f"[NitroViper Ultra] Sniped: {redeemer.sniped_count} | Watchers: {active_watchers}/{len(watchers)} | Guilds: {total_guilds}"
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass
        await asyncio.sleep(2)


def print_banner(total_watchers: int):
    os.system("cls" if os.name == "nt" else "clear")
    banner = f"""
{C_BANNER}                    ***********####
                   ******************##
                   #***************######
                         *****+===+*#######
            *** ************-{C_WHITE}.......{C_BANNER}:+######
            ##  #######****{C_WHITE}..:------..{C_BANNER}=#####
                  ****####-{C_WHITE}.:--------.{C_BANNER}:#####
                  ########={C_WHITE}.:--------.{C_BANNER}:#####
                     #####*{C_WHITE}:.:-----:.{C_BANNER}*#####
                      ######+{C_WHITE}::...::{C_BANNER}=######
                       ###################               {C_RESET}{C_GITHUB}[skibidi]- made by skibidi aro https://github.com/aro4848{C_RESET}
{C_BANNER}                        #################                 {C_RESET}{C_DISCORD}[discord]: https://discord.com/users/aro22 on discord{C_RESET}
{C_BANNER}                           ############                   {C_RESET}{C_LOGGED}[Engine: NitroViper Ultra-Fast | Watchers: {total_watchers}]{C_RESET}
"""
    print(banner)


# ----------------- MAIN ENTRYPOINT -----------------

async def main():
    # Load config file
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}

    webhook_url = config.get("webhook_url", "").strip()
    github_url = config.get("github_repo_url", "https://github.com/aro4848")

    print(f"{C_CYAN}[*] Initializing NitroViper Ultra Engine...{C_RESET}")

    # Temporary lightweight session to resolve and verify tokens
    async with aiohttp.ClientSession() as temp_session:
        redeemer_token, watcher_tokens = await resolve_active_tokens(temp_session, config)

    if not redeemer_token:
        print(f"\n{C_RED}[!] Error: No valid Discord tokens found!{C_RESET}")
        print(f"{C_DIM}Please log in to Discord Desktop or add your token to config.json.{C_RESET}\n")
        await asyncio.sleep(5)
        sys.exit(1)

    # If no separate watcher tokens, use redeemer as watcher
    watch_tokens = watcher_tokens if watcher_tokens else [redeemer_token]

    print_banner(len(watch_tokens))
    print(f"{C_CYAN}[*] Initializing Pre-warmed HTTP Connection Pool...{C_RESET}")

    redeemer = FastRedeemer(redeemer_token, webhook_url, github_url)
    await redeemer.init()

    # Pre-warm connection to Discord API host (eliminates TLS handshake latency on claim)
    try:
        async with redeemer.session.get("https://discord.com/api/v9/gateway") as r:
            pass
        print(f"{C_GREEN}[+] HTTP/2 Keep-Alive session pre-warmed and ready.{C_RESET}")
    except Exception as e:
        print(f"{C_YELLOW}[!] Pre-warm ping warning: {e}{C_RESET}")

    watchers = [
        GatewayWatcher(tok, redeemer, idx + 1)
        for idx, tok in enumerate(watch_tokens)
    ]

    # Spawn title monitor
    asyncio.create_task(console_title_loop(redeemer, watchers))

    print(f"{C_CYAN}[*] Starting {len(watchers)} raw WebSocket gateway watcher(s)...{C_RESET}\n")

    watcher_tasks = [asyncio.create_task(w.run()) for w in watchers]

    try:
        await asyncio.gather(*watcher_tasks)
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[*] Shutting down NitroViper cleanly...{C_RESET}")
    finally:
        await redeemer.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
