<div align="center">

**مدير اتصالات SSH احترافي لأوبونتو — واجهة رسومية + سطر أوامر، بمحرك واحد مشترك.**

`sss prod` · `sss prod nginx` · `sss prod --exec "uptime"`

[English](README.md) · [فارسی](README.fa.md) · **العربية** · [简体中文](README.zh.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Français](README.fr.md)

</div>

SSH Desk منتج حقيقي قابل للتثبيت (وليس نموذجًا تجريبيًا) لإدارة جميع خوادم SSH لديك: كلمات المرور تُخزَّن **فقط** في GNOME Keyring (خدمة Secret)، ومحرك SSH هو **OpenSSH الخاص بالنظام** نفسه، والطرفية المدمجة هي **PTY حقيقية** (vim/nano، الألوان، Ctrl+C، تغيير الحجم — كل شيء يعمل فعلًا).

- 🖥️ **واجهة رسومية** (PySide6): سمات داكنة/فاتحة، فارسي/إنجليزي مع دعم RTL كامل، تبويبات طرفية حقيقية، مدير ملفات SFTP، الأنفاق، المفاتيح، السجل
- ⌨️ **سطر أوامر** (Typer): يعمل **بدون** الواجهة الرسومية؛ اسم الأمر قابل للتغيير (`sss`، `cnc`، `sshgo`…)؛ إكمال تلقائي لـ bash/zsh يشمل أسماء الخوادم المختصرة
- 🔐 **الأمان أولًا**: تحقق صارم من مفتاح المضيف مع نافذة البصمة؛ الأسرار لا تصل أبدًا إلى قاعدة البيانات/السجلات/الوسائط؛ لا sshpass ولا `StrictHostKeyChecking=no`
- 🌐 **مقاوم لانقطاع الإنترنت**: سلسلة مرايا PyPI (الرسمي ← ArvanCloud إيران ← TUNA ← Aliyun ← Tencent) وتثبيت غير متصل بالكامل عبر `install.sh --offline`

📄 **[دليل المستخدم الكامل (PDF بالعربية)](docs/SSH-Desk-User-Guide-ar.pdf)** — 14 صفحة مصورة تشمل التثبيت دون اتصال، مرجع CLI الكامل، الطرفية، SFTP، الأنفاق، ونموذج الأمان. الدليل متوفر بـ 7 لغات أخرى أيضًا: [English](docs/SSH-Desk-User-Guide-en.pdf) · [فارسی](docs/SSH-Desk-User-Guide-fa.pdf) · [简体中文](docs/SSH-Desk-User-Guide-zh.pdf) · [Русский](docs/SSH-Desk-User-Guide-ru.pdf) · [Español](docs/SSH-Desk-User-Guide-es.pdf) · [Français](docs/SSH-Desk-User-Guide-fr.pdf)

---

## البدء السريع

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

ثم:

```bash
ssh-desk          # الواجهة الرسومية
sss add           # إضافة أول خادم
sss prod          # الاتصال (صدفة تفاعلية في طرفيتك)
```

لحزمة DEB والتثبيت اليدوي: [docs/INSTALLATION.md](docs/INSTALLATION.md).
لشبكات ضعيفة أو منقطعة: `bash scripts/download_wheels.sh --mirror-name ir` ثم `bash scripts/install.sh --offline`.

## سطر الأوامر في 30 ثانية

```bash
sss                      # ملخص + تلميحات
sss list                 # جدول الخوادم
sss add                  # معالج تفاعلي (أو عبر --alias/--host/...)
sss info prod            # التفاصيل الكاملة
sss test prod            # اختبار الاتصال
sss prod                 # صدفة تفاعلية في المسار الافتراضي
sss prod nginx           # الاتصال بمسار محفوظ
sss prod /etc/nginx      # الاتصال بمسار مطلق
sss prod --exec "uptime" # تنفيذ أمر واحد (لا شيء يُحفظ)
sss prod --user ubuntu --port 2222   # تجاوز لهذه الجلسة فقط
sss history              # سجل الاتصالات
sss current              # الجلسات النشطة + الأنفاق الجارية
sss tunnel db            # تشغيل نفق مسمّى (يستمر بعد إغلاق الطرفية)
sss config cli-name cnc  # إعادة تسمية الأمر على مستوى النظام
sss --help               # المرجع الكامل
```

## الميزات

| المجال | ما يعمل فعليًا |
| --- | --- |
| الخوادم | إنشاء/تعديل/حذف، أسماء مختصرة فريدة، مجموعات، وسوم، مفضلة، تكرار، بحث/فرز/تصفية |
| المصادقة | كلمة مرور (Keyring)، مفتاح خاص (+عبارة في Keyring)، SSH agent، تفاعلي |
| المسارات | مسار افتراضي + مسارات محفوظة باسم (`sss prod nginx`)، اقتباس آمن |
| الطرفية | PTY حقيقية (OpenSSH)، تبويبات متعددة، ألوان، vim/nano، تغيير الحجم، نسخ/لصق |
| الملفات | مدير SFTP بلوحتين: رفع/تنزيل/mkdir/تسمية/chmod/تحرير/حذف + نقل بين خادمين |
| المفاتيح | توليد Ed25519/RSA/ECDSA بصيغة OpenSSH، استيراد، بصمة، تصدير المفتاح العام، دليل `ssh-copy-id` |
| الأنفاق | Local / Remote / Dynamic SOCKS، تشغيل/إيقاف، خفي مستقل، تتبع الحالة |
| القفز | `ProxyCommand` عبر `ssh -W` من خلال أي خادم مسجَّل (سلاسل متداخلة مدعومة) |
| الأوامر | أوامر محفوظة لكل خادم أو عامة، تأكيد للأوامر الخطرة |
| السجل | اتصال/فصل، المدة، الحالة، الأخطاء (بدون محتوى الطرفية، بدون كلمات مرور) |
| استيراد/تصدير | استيراد `~/.ssh/config` بمعاينة وكشف التكرار، نسخ احتياطي/استعادة TOML (الأسرار اختيارية) |

## نموذج الأمان (النسخة المختصرة)

1. كلمات المرور/العبارات السرية تعيش **فقط** في Secret Service (GNOME Keyring)؛ قاعدة البيانات تخزن مرجعًا غير سري فقط.
2. يحصل OpenSSH على الأسرار عبر **مساعد askpass** مؤمَّن — لا وسائط أبدًا، لا بيئة أبدًا، لا sshpass أبدًا.
3. التحقق من مفاتيح المضيف إلزامي (`StrictHostKeyChecking=yes`): غير معروف ← نافذة البصمة؛ متغيّر ← تحذير صارم.
4. ملفات قاعدة البيانات/الإعدادات بأذونات `0600`/`0700`؛ السجلات منقّاة؛ لا خفيوت root.

التفاصيل الكاملة: [docs/SECURITY.md](docs/SECURITY.md).

## التطوير

```bash
pip install -e .[dev]
pytest          # 54 tests
ruff check .    # clean
```

المعمارية والتفاصيل الداخلية: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## المتطلبات

- أوبونتو 22.04 / 24.04+ (أو أي توزيعة دبيانية)
- بايثون 3.10+ (يُفضَّل 3.12)، `openssh-client`
- GNOME Keyring لتخزين كلمات المرور (`sudo apt install gnome-keyring`)

## الترخيص

MIT — انظر [LICENSE](LICENSE).
