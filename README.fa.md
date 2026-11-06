<div align="center">

**مدیر حرفه‌ای اتصال SSH برای اوبونتو — رابط گرافیکی + خط فرمان، با یک موتور مشترک.**

`sss prod` · `sss prod nginx` · `sss prod --exec "uptime"`

[English](README.md) · **فارسی** · [العربية](README.ar.md) · [简体中文](README.zh.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Français](README.fr.md)

</div>

SSH Desk یک محصول واقعی و قابل‌نصب است (نه یک نمونهٔ نمایشی) برای مدیریت همهٔ سرورهای SSH شما: رمزهای عبور **فقط** در GNOME Keyring (سرویس Secret) ذخیره می‌شوند، موتور SSH همان **OpenSSH سیستم** است و ترمینال داخلی یک **PTY واقعی** است (vim/nano، رنگ‌ها، Ctrl+C، تغییر اندازه — همه‌چیز واقعاً کار می‌کند).

- 🖥️ **رابط گرافیکی** (PySide6): تم تیره/روشن، فارسی/انگلیسی با RTL کامل، زبان‌های ترمینال واقعی، مدیر فایل SFTP، تونل‌ها، کلیدها، تاریخچه
- ⌨️ **خط فرمان** (Typer): بدون GUI هم کار می‌کند؛ نام دستور قابل تغییر (`sss`، `cnc`، `sshgo` و…)؛ تکمیل خودکار bash/zsh با تکمیل نام‌کوتاه سرورها
- 🔐 **امنیت در اولویت**: بررسی سخت‌گیرانهٔ Host Key با پنجرهٔ اثرانگشت؛ رازها هرگز در دیتابیس/لاگ/آرگومان نمی‌آیند؛ بدون sshpass و بدون `StrictHostKeyChecking=no`
- 🌐 **مقاوم به قطعی اینترنت**: زنجیرهٔ میرورهای PyPI (رسمی ← ArvanCloud ایران ← TUNA ← Aliyun ← Tencent) و نصب کاملاً آفلاین با `install.sh --offline`

📄 **[راهنمای کاربر کامل (PDF فارسی)](docs/SSH-Desk-User-Guide-fa.pdf)** — ۱۴ صفحهٔ مصور شامل نصب آفلاین، مرجع کامل CLI، ترمینال، SFTP، تونل‌ها و مدل امنیتی.

---

## شروع سریع

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

سپس:

```bash
ssh-desk          # رابط گرافیکی
sss add           # افزودن اولین سرور
sss prod          # اتصال (شِل تعاملی در ترمینال شما)
```

راهنمای بستهٔ DEB و نصب دستی: [docs/INSTALLATION.md](docs/INSTALLATION.md).
برای اینترنت ضعیف/قطع: `bash scripts/download_wheels.sh --mirror-name ir` و سپس `bash scripts/install.sh --offline`.

## خط فرمان در ۳۰ ثانیه

```bash
sss                      # خلاصه + راهنما
sss list                 # جدول سرورها
sss add                  # جادوگر تعاملی (یا با --alias/--host/...)
sss info prod            # جزئیات کامل
sss test prod            # آزمایش اتصال
sss prod                 # شِل تعاملی روی مسیر پیش‌فرض
sss prod nginx           # اتصال به مسیر ذخیره‌شده
sss prod /etc/nginx      # اتصال به مسیر مطلق
sss prod --exec "uptime" # اجرای یک دستور (هیچ‌چیز ذخیره نمی‌شود)
sss prod --user ubuntu --port 2222   # override فقط برای همین اجرا
sss history              # تاریخچهٔ اتصال‌ها
sss current              # نشست‌های فعال + تونل‌های در حال اجرا
sss tunnel db            # اجرای تونل نام‌دار (از ترمینال جدا می‌ماند)
sss config cli-name cnc  # تغییر نام دستور در کل سیستم
sss --help               # مرجع کامل
```

## امکانات

| حوزه | چه چیزهایی واقعاً کار می‌کند |
| --- | --- |
| سرورها | CRUD، نام‌کوتاه یکتا، گروه‌ها، برچسب‌ها، علاقه‌مندی، Duplicate، جست‌وجو/مرتب‌سازی/فیلتر |
| احراز هویت | رمز (Keyring)، کلید خصوصی (+گذرواژه در Keyring)، SSH agent، تعاملی |
| مسیرها | مسیر پیش‌فرض + مسیرهای نام‌دار ذخیره‌شده (`sss prod nginx`)، نقل‌قول امن |
| ترمینال | PTY واقعی (OpenSSH)، چندزبانه، رنگ‌ها، vim/nano، تغییر اندازه، کپی/پیست |
| فایل‌ها | مدیر SFTP دوپنجره‌ای: آپلود/دانلود/mkdir/rename/chmod/ویرایش/حذف + انتقال سرور↔سرور |
| کلیدها | تولید Ed25519/RSA/ECDSA در قالب OpenSSH، درون‌ریزی، اثرانگشت، خروجی کلید عمومی، راهنمای `ssh-copy-id` |
| تونل‌ها | Local / Remote / Dynamic SOCKS، شروع/توقف، دیمن مستقل، ردیابی وضعیت |
| Jump Host | `ProxyCommand` با `ssh -W` از طریق هر سرور ثبت‌شده (زنجیرهٔ تو در تو پشتیبانی می‌شود) |
| دستورات | دستورات ذخیره‌شدهٔ هر سرور یا سراسری، تأیید برای دستورهای خطرناک |
| تاریخچه | اتصال/قطع، مدت، وضعیت، خطاها (بدون محتوای ترمینال، بدون رمز) |
| درون‌ریزی/برون‌بری | درون‌ریزی `~/.ssh/config` با پیش‌نمایش و کشف تکراری، پشتیبان/بازگردانی TOML (رمزها opt-in) |

## مدل امنیتی (نسخهٔ کوتاه)

1. رمزها/گذرواژه‌ها **فقط** در Secret Service (GNOME Keyring) زندگی می‌کنند؛ دیتابیس فقط یک ارجاع بدون‌راز دارد.
2. OpenSSH رازها را از طریق **askpass helper** امن می‌گیرد — هرگز argv، هرگز محیط، هرگز sshpass.
3. کلیدهای میزبان الزامی است (`StrictHostKeyChecking=yes`): ناشناس ← پنجرهٔ اثرانگشت؛ تغییر ← هشدار سخت.
4. فایل‌های دیتابیس/پیکربندی با مجوز `0600`/`0700`؛ لاگ‌ها پاک‌سازی می‌شوند؛ بدون دیمن root.

جزئیات کامل: [docs/SECURITY.md](docs/SECURITY.md).

## توسعه

```bash
pip install -e .[dev]
pytest          # 54 tests
ruff check .    # clean
```

معماری و جزئیات داخلی: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## پیش‌نیازها

- اوبونتو 22.04 / 24.04+ (یا هر توزیع دبیان‌پایه)
- پایتون 3.10+ (3.12 پیشنهادی)، `openssh-client`
- GNOME Keyring برای ذخیرهٔ رمزها (`sudo apt install gnome-keyring`)

## مجوز

MIT — ببینید [LICENSE](LICENSE).
