"""Bilingual strings (English / Persian) with RTL support."""

from ssh_desk.core.config import DEFAULTS

_current_lang = DEFAULTS["language"]

STRINGS: dict[str, dict[str, str]] = {
    # ----- generic
    "app_name": {"en": "SSH Desk", "fa": "اسک دیسک"},
    "ok": {"en": "OK", "fa": "تأیید"},
    "cancel": {"en": "Cancel", "fa": "انصراف"},
    "close": {"en": "Close", "fa": "بستن"},
    "save": {"en": "Save", "fa": "ذخیره"},
    "delete": {"en": "Delete", "fa": "حذف"},
    "edit": {"en": "Edit", "fa": "ویرایش"},
    "add": {"en": "Add", "fa": "افزودن"},
    "search": {"en": "Search...", "fa": "جست‌وجو..."},
    "refresh": {"en": "Refresh", "fa": "بازخوانی"},
    "connect": {"en": "Connect", "fa": "اتصال"},
    "disconnect": {"en": "Disconnect", "fa": "قطع اتصال"},
    "reconnect": {"en": "Reconnect", "fa": "اتصال مجدد"},
    "test": {"en": "Test", "fa": "تست"},
    "yes": {"en": "Yes", "fa": "بله"},
    "no": {"en": "No", "fa": "خیر"},
    "name": {"en": "Name", "fa": "نام"},
    "alias": {"en": "Alias", "fa": "نام مستعار"},
    "host": {"en": "Host", "fa": "میزبان"},
    "port": {"en": "Port", "fa": "پورت"},
    "username": {"en": "Username", "fa": "نام کاربری"},
    "password": {"en": "Password", "fa": "رمز عبور"},
    "group": {"en": "Group", "fa": "گروه"},
    "tags": {"en": "Tags", "fa": "برچسب‌ها"},
    "description": {"en": "Description", "fa": "توضیحات"},
    "favorite": {"en": "Favorite", "fa": "موردعلاقه"},
    "path": {"en": "Path", "fa": "مسیر"},
    "status": {"en": "Status", "fa": "وضعیت"},
    "actions": {"en": "Actions", "fa": "عملیات"},
    "confirm": {"en": "Confirmation", "fa": "تأیید عملیات"},
    "warning": {"en": "Warning", "fa": "هشدار"},
    "error": {"en": "Error", "fa": "خطا"},
    "none": {"en": "None", "fa": "هیچ"},
    "copy": {"en": "Copy", "fa": "کپی"},
    "paste": {"en": "Paste", "fa": "چسباندن"},
    "running": {"en": "Running", "fa": "در حال اجرا"},
    "stopped": {"en": "Stopped", "fa": "متوقف"},
    "settings": {"en": "Settings", "fa": "تنظیمات"},
    "theme": {"en": "Theme", "fa": "پوسته"},
    "language": {"en": "Language", "fa": "زبان"},
    "dark": {"en": "Dark", "fa": "تاریک"},
    "light": {"en": "Light", "fa": "روشن"},
    "connected": {"en": "Connected", "fa": "متصل"},
    "failed": {"en": "Failed", "fa": "ناموفق"},
    "loading": {"en": "Loading...", "fa": "در حال بارگذاری..."},
    # ----- pages
    "page_dashboard": {"en": "Dashboard", "fa": "میزکار"},
    "page_servers": {"en": "Servers", "fa": "سرورها"},
    "page_terminal": {"en": "Terminal", "fa": "ترمینال"},
    "page_files": {"en": "Files", "fa": "فایل‌ها"},
    "page_keys": {"en": "SSH Keys", "fa": "کلیدهای SSH"},
    "page_tunnels": {"en": "Port Forwarding", "fa": "تونل‌ها"},
    "page_commands": {"en": "Commands", "fa": "دستورها"},
    "page_history": {"en": "History", "fa": "تاریخچه"},
    # ----- dashboard
    "stat_total_servers": {"en": "Total servers", "fa": "کل سرورها"},
    "stat_active_sessions": {"en": "Active sessions", "fa": "اتصال‌های جاری"},
    "stat_favorites": {"en": "Favorites", "fa": "موردعلاقه‌ها"},
    "stat_tunnels": {"en": "Running tunnels", "fa": "تونل‌های فعال"},
    "recent_connections": {"en": "Recent connections", "fa": "آخرین اتصال‌ها"},
    "quick_connect": {"en": "Quick connect", "fa": "اتصال سریع"},
    "ssh_status": {"en": "SSH engine", "fa": "موتور SSH"},
    "ssh_ready": {"en": "OpenSSH available", "fa": "OpenSSH در دسترس است"},
    "ssh_missing": {"en": "OpenSSH not found - install openssh-client", "fa": "OpenSSH یافت نشد - openssh-client را نصب کنید"},
    "dash_empty": {"en": "No recent connections yet", "fa": "هنوز اتصالی ثبت نشده است"},
    # ----- servers
    "add_server": {"en": "Add server", "fa": "افزودن سرور"},
    "edit_server": {"en": "Edit server", "fa": "ویرایش سرور"},
    "duplicate": {"en": "Duplicate", "fa": "تکثیر"},
    "details": {"en": "Details", "fa": "جزئیات"},
    "filter_group": {"en": "Group", "fa": "گروه"},
    "all_groups": {"en": "All groups", "fa": "همه گروه‌ها"},
    "sort": {"en": "Sort", "fa": "مرتب‌سازی"},
    "confirm_delete_server": {"en": "Delete server '{name}'?\nIts stored secret will be removed from the keyring.", "fa": "سرور '{name}' حذف شود؟\nرمز ذخیره‌شده آن نیز از Keyring حذف می‌شود."},
    "servers_empty": {"en": "No servers yet.\nClick 'Add server' to create your first one.", "fa": "هنوز سروری ثبت نشده است.\nبا «افزودن سرور» اولین سرور را بسازید."},
    "server_saved": {"en": "Server saved", "fa": "سرور ذخیره شد"},
    "server_deleted": {"en": "Server deleted", "fa": "سرور حذف شد"},
    "connection_ok": {"en": "Connection successful ({ms} ms)", "fa": "اتصال موفق ({ms} میلی‌ثانیه)"},
    "connection_failed": {"en": "Connection failed", "fa": "اتصال ناموفق"},
    "testing": {"en": "Testing connection...", "fa": "در حال تست اتصال..."},
    # ----- server dialog
    "tab_general": {"en": "General", "fa": "عمومی"},
    "tab_auth": {"en": "Authentication", "fa": "احراز هویت"},
    "tab_connection": {"en": "Connection", "fa": "اتصال"},
    "tab_advanced": {"en": "Advanced", "fa": "پیشرفته"},
    "auth_password": {"en": "Password (GNOME Keyring)", "fa": "رمز عبور (GNOME Keyring)"},
    "auth_key": {"en": "SSH private key", "fa": "کلید خصوصی SSH"},
    "auth_agent": {"en": "SSH agent", "fa": "SSH Agent"},
    "auth_interactive": {"en": "Interactive (type each time)", "fa": "تعاملی (هر بار تایپ شود)"},
    "store_password": {"en": "Store password in system keyring", "fa": "ذخیره رمز در Keyring سیستم"},
    "default_path": {"en": "Default path", "fa": "مسیر پیش‌فرض"},
    "saved_paths": {"en": "Saved paths", "fa": "مسیرهای ذخیره‌شده"},
    "path_name": {"en": "Name", "fa": "نام"},
    "path_value": {"en": "Remote path", "fa": "مسیر روی سرور"},
    "is_default": {"en": "Default", "fa": "پیش‌فرض"},
    "timeout": {"en": "Connection timeout (s)", "fa": "مهلت اتصال (ثانیه)"},
    "keepalive": {"en": "Keep-alive interval (s)", "fa": "فاصله Keep-Alive (ثانیه)"},
    "compression": {"en": "Compression", "fa": "فشرده‌سازی"},
    "forward_agent": {"en": "Forward agent", "fa": "ارجاع Agent"},
    "jump_host": {"en": "Jump host (bastion)", "fa": "سرور پرشی"},
    "custom_options": {"en": "Custom SSH options (one per line: Key Value)", "fa": "گزینه‌های سفارشی SSH (هر خط: Key Value)"},
    "preferred_auth": {"en": "Preferred auth methods", "fa": "روش‌های ترجیحی احراز هویت"},
    "select_key": {"en": "Select key", "fa": "انتخاب کلید"},
    "invalid_form": {"en": "Please fix the highlighted fields", "fa": "فیلدهای مشخص‌شده را اصلاح کنید"},
    # ----- details
    "auth_method": {"en": "Auth method", "fa": "روش احراز هویت"},
    "last_connection": {"en": "Last connection", "fa": "آخرین اتصال"},
    "show_password": {"en": "Show password", "fa": "نمایش رمز"},
    "hide_password": {"en": "Hide password", "fa": "پنهان کردن رمز"},
    "confirm_reveal": {"en": "The stored password will be shown.\nType the alias '{alias}' to confirm.", "fa": "رمز ذخیره‌شده نمایش داده می‌شود.\nبرای تأیید، نام مستعار سرور را تایپ کنید: '{alias}'"},
    "password_copied": {"en": "Password copied (clipboard clears automatically)", "fa": "رمز کپی شد (کلیپ‌بورد خودکار پاک می‌شود)"},
    "linked_keys": {"en": "Related keys", "fa": "کلیدهای مرتبط"},
    "ready_commands": {"en": "Ready commands", "fa": "دستورهای آماده"},
    "connection_history": {"en": "Connection history", "fa": "تاریخچه اتصال"},
    # ----- terminal
    "new_session": {"en": "New session", "fa": "نشست جدید"},
    "end_session": {"en": "End session", "fa": "پایان نشست"},
    "font_plus": {"en": "A+", "fa": "A+"},
    "font_minus": {"en": "A-", "fa": "A-"},
    "terminal_empty": {"en": "No open sessions.\nUse 'New session' to connect to a server.", "fa": "نشستی باز نیست.\nبا «نشست جدید» به یک سرور متصل شوید."},
    "select_server": {"en": "Select server", "fa": "انتخاب سرور"},
    "session_ended": {"en": "Session ended (code {code})", "fa": "نشست پایان یافت (کد {code})"},
    # ----- files
    "local": {"en": "Local", "fa": "محلی"},
    "remote": {"en": "Remote", "fa": "سرور"},
    "upload": {"en": "Upload", "fa": "آپلود"},
    "download": {"en": "Download", "fa": "دانلود"},
    "mkdir": {"en": "New folder", "fa": "پوشه جدید"},
    "rename": {"en": "Rename", "fa": "تغییر نام"},
    "chmod": {"en": "Permissions", "fa": "مجوزها"},
    "transfer_to": {"en": "Send to server...", "fa": "ارسال به سرور..."},
    "edit_file": {"en": "Edit", "fa": "ویرایش"},
    "files_not_connected": {"en": "Select a server and click Connect to browse files.", "fa": "برای مرور فایل‌ها، سرور را انتخاب و اتصال بزنید."},
    "files_connected": {"en": "Connected via SFTP", "fa": "با SFTP متصل شد"},
    "size": {"en": "Size", "fa": "حجم"},
    "modified": {"en": "Modified", "fa": "آخرین تغییر"},
    "permissions": {"en": "Permissions", "fa": "مجوزها"},
    "confirm_delete_file": {"en": "Delete '{name}' on the server?", "fa": "'{name}' از سرور حذف شود؟"},
    # ----- keys
    "generate_key": {"en": "Generate key", "fa": "ساخت کلید"},
    "import_key": {"en": "Import key", "fa": "افزودن کلید"},
    "export_pub": {"en": "Export public key", "fa": "خروجی کلید عمومی"},
    "install_guide": {"en": "Install on server", "fa": "نصب روی سرور"},
    "key_type": {"en": "Type", "fa": "نوع"},
    "fingerprint": {"en": "Fingerprint", "fa": "اثر انگشت"},
    "passphrase": {"en": "Passphrase", "fa": "عبارت عبور"},
    "confirm_delete_key": {"en": "Remove key '{name}' from SSH Desk? Key files can also be deleted.", "fa": "کلید '{name}' از اسک دیسک حذف شود؟ فایل‌های کلید نیز قابل حذف‌اند."},
    "also_delete_files": {"en": "Also delete key files from disk", "fa": "فایل‌های کلید هم از دیسک حذف شوند"},
    "keys_empty": {"en": "No SSH keys registered yet.", "fa": "هنوز کلیدی ثبت نشده است."},
    "copy_id_cmd": {"en": "Run this command to install the public key on the server:", "fa": "برای نصب کلید عمومی روی سرور این دستور را اجرا کنید:"},
    # ----- tunnels
    "new_tunnel": {"en": "New tunnel", "fa": "تونل جدید"},
    "tunnel_type": {"en": "Type", "fa": "نوع"},
    "local_fwd": {"en": "Local (-L)", "fa": "محلی (-L)"},
    "remote_fwd": {"en": "Remote (-R)", "fa": "معکوس (-R)"},
    "dynamic_fwd": {"en": "Dynamic SOCKS (-D)", "fa": "پویا / SOCKS (-D)"},
    "local_bind": {"en": "Local bind host", "fa": "هاست محلی"},
    "local_port": {"en": "Local port", "fa": "پورت محلی"},
    "remote_target": {"en": "Remote host", "fa": "میزبان مقصد"},
    "remote_port": {"en": "Remote port", "fa": "پورت مقصد"},
    "start": {"en": "Start", "fa": "شروع"},
    "stop": {"en": "Stop", "fa": "توقف"},
    "tunnels_empty": {"en": "No tunnels defined yet.", "fa": "هنوز تونلی تعریف نشده است."},
    "tunnel_started": {"en": "Tunnel started", "fa": "تونل شروع شد"},
    "tunnel_stopped": {"en": "Tunnel stopped", "fa": "تونل متوقف شد"},
    # ----- commands
    "new_command": {"en": "New command", "fa": "دستور جدید"},
    "command": {"en": "Command", "fa": "دستور"},
    "category": {"en": "Category", "fa": "دسته"},
    "requires_confirm": {"en": "Ask for confirmation before running", "fa": "پیش از اجرا تأیید گرفته شود"},
    "run": {"en": "Run", "fa": "اجرا"},
    "global_cmd": {"en": "Global (all servers)", "fa": "عمومی (همه سرورها)"},
    "commands_empty": {"en": "No saved commands yet.", "fa": "هنوز دستوری ذخیره نشده است."},
    "confirm_run_command": {"en": "Run this command on '{server}'?\n\n{command}", "fa": "این دستور روی '{server}' اجرا شود؟\n\n{command}"},
    # ----- history
    "when": {"en": "Connected at", "fa": "زمان اتصال"},
    "duration": {"en": "Duration", "fa": "مدت"},
    "clear_history": {"en": "Clear history", "fa": "پاک‌کردن تاریخچه"},
    "confirm_clear_history": {"en": "Delete the entire connection history?", "fa": "کل تاریخچه اتصال حذف شود؟"},
    "history_empty": {"en": "No connections recorded yet.", "fa": "هنوز اتصالی ثبت نشده است."},
    # ----- settings
    "cli_command_name": {"en": "Terminal command name", "fa": "نام دستور ترمینال"},
    "apply": {"en": "Apply", "fa": "اعمال"},
    "keyring_status": {"en": "Keyring (Secret Service)", "fa": "Keyring (سرویس Secret)"},
    "keyring_ok": {"en": "Available", "fa": "در دسترس"},
    "keyring_missing": {"en": "Unavailable - run: sudo apt install gnome-keyring", "fa": "در دسترس نیست - اجرا کنید: sudo apt install gnome-keyring"},
    "backup": {"en": "Backup", "fa": "پشتیبان‌گیری"},
    "restore": {"en": "Restore", "fa": "بازیابی"},
    "import_ssh_config": {"en": "Import ~/.ssh/config", "fa": "وارد کردن ~/.ssh/config"},
    "default_port": {"en": "Default SSH port", "fa": "پورت پیش‌فرض SSH"},
    "terminal_font": {"en": "Terminal font size", "fa": "اندازه فونت ترمینال"},
    "include_secrets": {"en": "Include stored passwords (unsafe)", "fa": "رمزهای ذخیره‌شده هم ذخیره شود (ناامن)"},
    "settings_saved": {"en": "Settings saved", "fa": "تنظیمات ذخیره شد"},
    "cli_renamed": {"en": "Terminal command updated", "fa": "نام دستور ترمینال به‌روزرسانی شد"},
    "purge_secrets": {"en": "Purge all stored secrets", "fa": "حذف همه رمزهای ذخیره‌شده"},
    "confirm_purge": {"en": "Delete ALL passwords stored in the system keyring by SSH Desk?", "fa": "همه رمزهای ذخیره‌شده در Keyring حذف شوند؟"},
    "about": {"en": "About", "fa": "درباره"},
    # ----- host key dialog
    "hostkey_unknown_title": {"en": "Unknown host", "fa": "میزبان ناشناس"},
    "hostkey_unknown_msg": {"en": "The host '{host}' is not in the known hosts list.\nVerify the fingerprint and accept it.", "fa": "میزبان '{host}' در فهرست میزبان‌های شناخته‌شده نیست.\nاثر انگشت را بررسی و تأیید کنید."},
    "hostkey_accept": {"en": "Accept and store", "fa": "تأیید و ذخیره"},
    "hostkey_reject": {"en": "Reject", "fa": "رد کردن"},
    # ----- toasts
    "saved": {"en": "Saved", "fa": "ذخیره شد"},
    "deleted": {"en": "Deleted", "fa": "حذف شد"},
    "copied": {"en": "Copied to clipboard", "fa": "کپی شد"},
    "shortcut_new_server": {"en": "Ctrl+N - new server", "fa": "Ctrl+N - سرور جدید"},
    "shortcut_new_session": {"en": "Ctrl+K - new terminal session", "fa": "Ctrl+K - نشست ترمینال جدید"},
    # ----- sessions status bar
    "statusbar_sessions": {"en": "{n} active session(s)", "fa": "{n} نشست فعال"},
    "statusbar_tunnels": {"en": "{n} tunnel(s) running", "fa": "{n} تونل فعال"},
}


def set_language(lang: str) -> None:
    global _current_lang
    _current_lang = "fa" if str(lang).lower().startswith("fa") else "en"


def current_language() -> str:
    return _current_lang


def is_rtl() -> bool:
    return _current_lang == "fa"


def tr(key: str, **kwargs) -> str:
    entry = STRINGS.get(key)
    text = entry.get(_current_lang, entry.get("en", key)) if entry else key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
