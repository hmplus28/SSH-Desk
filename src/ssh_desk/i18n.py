"""Multilingual strings for SSH Desk: 7 languages (en, fa, ar, zh, ru, es, fr).

State lives here (single source of truth); ``ssh_desk.gui.i18n`` re-exports it.
The other five languages are merged in from ``ssh_desk.i18n_extra``.
"""

from ssh_desk.core.config import DEFAULTS

LANGS: tuple[str, ...] = ("en", "fa", "ar", "zh", "ru", "es", "fr")
RTL_LANGS: tuple[str, ...] = ("fa", "ar")

# Native names shown in the settings combo (and reused by CLI/GUI).
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "fa": "فارسی",
    "ar": "العربية",
    "zh": "简体中文",
    "ru": "Русский",
    "es": "Español",
    "fr": "Français",
}

LANG_PREFIXES: tuple[str, ...] = ("fa", "ar", "zh", "ru", "es", "fr")

_current_lang: str = str(DEFAULTS["language"])

# ---------------------------------------------------------------- strings (en + fa base)
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
    "key_comment": {"en": "Comment", "fa": "کامنت"},
    "key_private_key": {"en": "Private key", "fa": "کلید خصوصی"},
    "key_copy_storage": {"en": "Copy into SSH Desk storage (0600)", "fa": "کپی در حافظه SSH Desk (0600)"},
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
    # ----- misc GUI literals
    "invalid_octal": {"en": "Invalid octal mode", "fa": "مقدار هشت‌گانی نامعتبر"},
    "no_other_server": {"en": "No other server available", "fa": "سرور دیگری در دسترس نیست"},
    # ----- CLI messages
    "cli_group_not_found": {"en": "Group '{group}' not found", "fa": "گروه '{group}' یافت نشد"},
    "cli_no_servers_add": {"en": "No servers yet. Add one with: {cmd} add", "fa": "هنوز سروری ثبت نشده. با {cmd} add یکی اضافه کنید"},
    "cli_server_saved": {"en": "Server '{alias}' saved (id={id})", "fa": "سرور '{alias}' ذخیره شد (id={id})"},
    "cli_password_stored": {"en": "Password stored securely in the system keyring (Secret Service)", "fa": "رمز به‌صورت امن در Keyring سیستم ذخیره شد (Secret Service)"},
    "cli_connect_now": {"en": "Connect now:  {cmd} {alias}", "fa": "اتصال فوری:  {cmd} {alias}"},
    "cli_confirmation_failed": {"en": "Confirmation failed - password not shown", "fa": "تأیید ناموفق بود - رمز نمایش داده نشد"},
    "cli_no_password": {"en": "No password stored for this server", "fa": "رمزی برای این سرور ذخیره نشده است"},
    "cli_test_ok": {"en": "{alias}: connection successful ({ms} ms)", "fa": "{alias}: اتصال موفق ({ms} میلی‌ثانیه)"},
    "cli_server_updated": {"en": "Server '{alias}' updated", "fa": "سرور '{alias}' به‌روزرسانی شد"},
    "cli_edit_prompt": {"en": "Press Enter to keep the current value. Type 'done' (or empty on field name) to finish.", "fa": "برای حفظ مقدار فعلی Enter بزنید. برای پایان، 'done' تایپ کنید (یا نام فیلد را خالی بگذارید)."},
    "cli_invalid_selection": {"en": "Invalid selection", "fa": "انتخاب نامعتبر"},
    "cli_nothing_changed": {"en": "Nothing changed", "fa": "تغییری اعمال نشد"},
    "cli_aborted": {"en": "Aborted", "fa": "لغو شد"},
    "cli_server_deleted": {"en": "Server '{alias}' deleted (secret removed from keyring)", "fa": "سرور '{alias}' حذف شد (رمز از Keyring پاک شد)"},
    "cli_search_nomatch": {"en": "No servers match '{term}'", "fa": "هیچ سروری با '{term}' مطابقت ندارد"},
    "cli_no_history": {"en": "No connection history yet", "fa": "هنوز تاریخچه اتصالی وجود ندارد"},
    "cli_no_sessions": {"en": "No active SSH sessions", "fa": "نشست SSH فعالی وجود ندارد"},
    "cli_config_file": {"en": "Config file: {path}", "fa": "فایل پیکربندی: {path}"},
    "cli_database": {"en": "Database:    {path}", "fa": "پایگاه داده:    {path}"},
    "cli_data_dir": {"en": "Data dir:    {path}", "fa": "پوشه داده:    {path}"},
    "cli_cli_renamed": {"en": "Terminal command is now: {name}", "fa": "نام دستور ترمینال اکنون: {name}"},
    "cli_path_hint": {"en": "If it is not found, ensure ~/.local/bin is in your PATH and open a new terminal.", "fa": "اگر یافت نشد، مطمئن شوید ~/.local/bin در PATH است و یک ترمینال جدید باز کنید."},
    "cli_completions_installed": {"en": "{shell} completions installed: {path}", "fa": "تکمیل خودکار {shell} نصب شد: {path}"},
    "cli_no_tunnels": {"en": "No tunnels defined. Create one in the GUI (Tunnels page) or via API.", "fa": "تونلی تعریف نشده. آن را در رابط گرافیکی (صفحه تونل‌ها) بسازید."},
    "cli_tunnel_running": {"en": "Tunnel '{name}' is running ({binding})", "fa": "تونل '{name}' در حال اجراست ({binding})"},
    "cli_tunnel_failed": {"en": "Tunnel '{name}' failed to start: {error}", "fa": "تونل '{name}' شروع نشد: {error}"},
    "cli_tunnel_stopped": {"en": "Tunnel '{name}' stopped", "fa": "تونل '{name}' متوقف شد"},
    "cli_tunnel_not_found": {"en": "Tunnel '{name}' not found", "fa": "تونل '{name}' یافت نشد"},
    "cli_no_keys": {"en": "No SSH keys registered", "fa": "کلید SSH ثبت نشده است"},
    "cli_key_generated": {"en": "Key '{name}' generated ({type})", "fa": "کلید '{name}' ساخته شد ({type})"},
    "cli_key_pub_hint": {"en": "Public key: {path}", "fa": "کلید عمومی: {path}"},
    "cli_key_registered": {"en": "Key '{name}' registered ({type}, {fingerprint})", "fa": "کلید '{name}' ثبت شد ({type}، {fingerprint})"},
    "cli_key_not_found": {"en": "Key '{name}' not found", "fa": "کلید '{name}' یافت نشد"},
    "cli_key_removed": {"en": "Key '{name}' removed", "fa": "کلید '{name}' حذف شد"},
    "cli_import_none": {"en": "No importable Host entries found", "fa": "هیچ ورودی Host قابل وارد کردن یافت نشد"},
    "cli_import_dryrun": {"en": "Dry run. Re-run with --apply to import.", "fa": "اجرای آزمایشی. برای وارد کردن واقعی با --apply اجرا کنید."},
    "cli_import_done": {"en": "Imported {created} server(s), skipped {skipped}", "fa": "{created} سرور وارد شد، {skipped} مورد رد شد"},
    "cli_export_done": {"en": "Exported {n} server(s) to {file}", "fa": "{n} سرور به فایل {file} برون‌سپاری شد"},
    "cli_export_secrets": {"en": "Secrets were included in this export - protect the file!", "fa": "رمزها در این خروجی گنجانده شده‌اند - فایل را محافظت کنید!"},
    "cli_backup_done": {"en": "Backup written to {file} ({n} servers)", "fa": "پشتیبان در {file} نوشته شد ({n} سرور)"},
    "cli_no_ssh": {"en": "OpenSSH client not found - install it with: sudo apt install openssh-client", "fa": "OpenSSH یافت نشد - نصب کنید: sudo apt install openssh-client"},
    "cli_cli_installed": {"en": "Terminal command installed: {name}", "fa": "دستور ترمینال نصب شد: {name}"},
    "cli_not_in_path": {"en": "{dir} is not in PATH. Add it to your ~/.bashrc:", "fa": "{dir} در PATH نیست. آن را به ~/.bashrc اضافه کنید:"},
    "cli_purge_skipped": {"en": "Keyring purge skipped: {reason}", "fa": "پاک‌سازی Keyring رد شد: {reason}"},
    "cli_purged": {"en": "Data removed. Purged {n} secret(s) from the keyring.", "fa": "داده‌ها حذف شد. {n} رمز از Keyring پاک شد."},
    "cli_more_servers": {"en": "  ... and {n} more (run '{cmd} list')", "fa": "  ... و {n} مورد دیگر (اجرای '{cmd} list')"},
    "cli_first_server": {"en": "No servers yet. Add your first server: {cmd} add", "fa": "هنوز سروری ثبت نشده. اولین سرور را اضافه کنید: {cmd} add"},
    "cli_hint_connect": {"en": "Connect:            {cmd} <alias> [path]", "fa": "اتصال:            {cmd} <alias> [path]"},
    "cli_hint_exec": {"en": "Run a command:      {cmd} <alias> --exec 'uptime'", "fa": "اجرای دستور:      {cmd} <alias> --exec 'uptime'"},
    "cli_hint_help": {"en": "Help & full guide:  {cmd} --help", "fa": "راهنما و مستندات:  {cmd} --help"},
    "cli_password_label": {"en": "Password: ", "fa": "رمز: "},
    "cli_connecting": {"en": "Connecting to {host} ... (Ctrl+D or 'exit' to disconnect)", "fa": "در حال اتصال به {host} ... (Ctrl+D یا 'exit' برای قطع اتصال)"},
    "cli_active_sessions": {"en": "Active SSH sessions:", "fa": "نشست‌های SSH فعال:"},
    "cli_running_tunnels": {"en": "Running tunnels:", "fa": "تونل‌های فعال:"},
    "cli_passphrase_prompt": {"en": "Passphrase", "fa": "عبارت عبور"},
    "cli_fingerprint_label": {"en": "Fingerprint: ", "fa": "اثر انگشت: "},
    "cli_reveal_prompt": {"en": "Type the alias '{alias}' to confirm revealing the password", "fa": "برای نمایش رمز، نام مستعار سرور را تایپ کنید: '{alias}'"},
    "cli_delete_confirm": {"en": "Delete server '{alias}' ({user}@{host}) and its stored secret? Type 'DELETE' to confirm", "fa": "سرور '{alias}' ({user}@{host}) و رمز ذخیره‌شده آن حذف شود؟ برای تأیید 'DELETE' تایپ کنید"},
    "cli_field_number": {"en": "Field number to edit (empty=finish)", "fa": "شماره فیلد برای ویرایش (خالی=پایان)"},
    "cli_new_value": {"en": "New value for '{field}'", "fa": "مقدار جدید برای '{field}'"},
    "cli_key_remove_confirm": {"en": "Remove key '{name}' from SSH Desk? [y/N]", "fa": "کلید '{name}' از اسک دیسک حذف شود؟ [y/N]"},
    # ----- CLI table headers
    "h_fav": {"en": "FAV", "fa": "علاقه"},
    "h_alias": {"en": "ALIAS", "fa": "نام مستعار"},
    "h_name": {"en": "NAME", "fa": "نام"},
    "h_host": {"en": "HOST", "fa": "میزبان"},
    "h_port": {"en": "PORT", "fa": "پورت"},
    "h_user": {"en": "USER", "fa": "کاربر"},
    "h_group": {"en": "GROUP", "fa": "گروه"},
    "h_auth": {"en": "AUTH", "fa": "احراز"},
    "h_status": {"en": "STATUS", "fa": "وضعیت"},
    "h_field": {"en": "FIELD", "fa": "فیلد"},
    "h_value": {"en": "VALUE", "fa": "مقدار"},
    "h_path_name": {"en": "PATH NAME", "fa": "نام مسیر"},
    "h_remote_path": {"en": "REMOTE PATH", "fa": "مسیر مقصد"},
    "h_default": {"en": "DEFAULT", "fa": "پیش‌فرض"},
    "h_tags": {"en": "TAGS", "fa": "برچسب‌ها"},
    "h_server": {"en": "SERVER", "fa": "سرور"},
    "h_connected": {"en": "CONNECTED", "fa": "اتصال"},
    "h_disconnected": {"en": "DISCONNECTED", "fa": "قطع"},
    "h_duration": {"en": "DURATION", "fa": "مدت"},
    "h_error": {"en": "ERROR", "fa": "خطا"},
    "h_pid": {"en": "PID", "fa": "PID"},
    "h_type": {"en": "TYPE", "fa": "نوع"},
    "h_binding": {"en": "BINDING", "fa": "اتصال پورت"},
    "h_id": {"en": "ID", "fa": "ID"},
    "h_key": {"en": "KEY", "fa": "کلید"},
    "h_exists": {"en": "EXISTS", "fa": "موجود"},
}


def set_language(lang: str) -> None:
    """Accept a full locale (``fa_IR``, ``zh_CN.UTF-8``) or a bare code."""
    value = str(lang).lower().replace("_", "-")
    for code in LANG_PREFIXES:
        if value.startswith(code):
            globals()["_current_lang"] = code
            return
    globals()["_current_lang"] = "en"


def current_language() -> str:
    return _current_lang


def is_rtl() -> bool:
    return _current_lang in RTL_LANGS


def tr(key: str, **kwargs) -> str:
    entry = STRINGS.get(key)
    text = entry.get(_current_lang, entry.get("en", key)) if entry else key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


# Merge the other five languages (ar / zh / ru / es / fr).
from ssh_desk.i18n_extra import EXTRA_LANGS as _EXTRA_LANGS  # noqa: E402

for _lang, _table in _EXTRA_LANGS.items():
    for _key, _value in _table.items():
        if _key in STRINGS:
            STRINGS[_key][_lang] = _value
