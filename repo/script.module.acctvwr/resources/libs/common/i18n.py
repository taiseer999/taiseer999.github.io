# -*- coding: utf-8 -*-
"""
Arabic UI layer for AM Lite (script.module.acctmgr / script.module.acctvwr).

All user-facing text in the code is English. When the UI language resolves to
Arabic, tr() maps that text to Arabic at display time (exact match first, then
regex templates for strings carrying dynamic values). Internal values (add-on
names, setting ids, sync keys) are never touched because translation happens
only at the point text reaches the screen.

Language selection (setting `ui.language` in script.module.acctmgr):
    0 = Auto (follow Kodi interface language)   1 = Arabic   2 = English
"""
import re

import xbmc
import xbmcaddon
import xbmcgui

_ACTIVE = None


def is_arabic():
    global _ACTIVE
    if _ACTIVE is None:
        mode = '0'
        try:
            mode = xbmcaddon.Addon('script.module.acctmgr').getSetting('ui.language') or '0'
        except Exception:
            pass
        if mode == '1':
            _ACTIVE = True
        elif mode == '2':
            _ACTIVE = False
        else:
            try:
                _ACTIVE = (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower().startswith('ar')
            except Exception:
                _ACTIVE = False
    return _ACTIVE


# ---------------------------------------------------------------------------
# Exact strings
# ---------------------------------------------------------------------------
EXACT = {
    # Buttons / generic
    'Yes': 'نعم',
    'No': 'لا',
    'OK': 'موافق',
    'Ok': 'موافق',
    'Cancel': 'إلغاء',
    'Continue': 'متابعة',
    'Done': 'تم',
    'Proceed': 'متابعة',
    'Authorize': 'تفويض',
    'Configure': 'إعداد يدوي',
    'Sync': 'مزامنة',
    'Install': 'تثبيت',
    'Uninstall': 'إزالة',
    'None': 'لا يوجد',
    'Unknown': 'غير معروف',
    'Premium': 'مميز (Premium)',
    'Basic': 'أساسي',
    'Authorized': 'مفوَّض',
    'Not Active': 'غير نشط',
    'Are you sure?': 'هل أنت متأكد؟',

    # Sync / revoke
    'Sync in progress, please wait!': 'جارٍ المزامنة، يرجى الانتظار!',
    'Sync Complete!': 'اكتملت المزامنة!',
    'Force Closing Kodi!': 'جارٍ إغلاق Kodi إجبارياً!',
    'All Add-ons Revoked!': 'تم إلغاء التفويض من جميع الإضافات!',
    'All Data Cleared!': 'تم مسح جميع البيانات!',
    'You have not yet created a list of add-ons to authorize![CR]Would you like to create your list now?':
        'لم تُنشئ بعد قائمة بالإضافات المراد تفويضها![CR]هل تريد إنشاء القائمة الآن؟',
    'No services are authorized. You have no data to revoke!':
        'لا توجد خدمات مفوَّضة. لا توجد بيانات لإلغائها!',
    'WARNING! This will completely wipe all settings applied by AM Lite. Would you like to proceed?':
        'تحذير! سيؤدي هذا إلى مسح جميع الإعدادات التي طبّقها AM Lite بالكامل. هل تريد المتابعة؟',

    # Scrapers
    'Scraper Module Installed!': 'تم تثبيت وحدة الـ Scrapers!',
    'All supported scraper modules are installed!': 'جميع وحدات الـ Scrapers المدعومة مثبّتة!',
    'No scraper modules are installed!': 'لا توجد وحدات Scrapers مثبّتة!',
    'Choose Scraper Package': 'اختر حزمة الـ Scrapers',
    'Choose scraper package': 'اختر حزمة الـ Scrapers',
    'Select Scraper Package to Sync': 'اختر حزمة الـ Scrapers للمزامنة',
    'No external scrapers installed!': 'لا توجد Scrapers خارجية مثبّتة!',
    'How would you like to proceed?\n1. Sync this scraper package to all add-ons\n2. Configure add-ons manually?':
        'كيف تريد المتابعة؟\n1. مزامنة حزمة الـ Scrapers هذه مع جميع الإضافات\n2. إعداد الإضافات يدوياً؟',
    'Change External Scraper Package': 'تغيير حزمة الـ Scrapers الخارجية',
    'External Providers': 'المزوّدات الخارجية',

    # Tools
    'No supported add-ons installed!': 'لا توجد إضافات مدعومة مثبّتة!',
    'No supported add-ons found!': 'لم يتم العثور على إضافات مدعومة!',
    'Source Select Set!': 'تم ضبط اختيار المصدر يدوياً!',
    'Autoplay Set!': 'تم ضبط التشغيل التلقائي!',
    'TMdb Helper is NOT installed!': 'إضافة TMDb Helper غير مثبّتة!',

    # TMDb Helper players
    'AM Lite - Choose TMDb Helper Players': 'AM Lite - اختر مشغّلات TMDb Helper',
    'AM Lite - Choose TMDb Helper Players to Install': 'AM Lite - اختر مشغّلات TMDb Helper لتثبيتها',
    'AM Lite - Choose TMDb Helper Players to Uninstall': 'AM Lite - اختر مشغّلات TMDb Helper لإزالتها',
    'Choose Players to Install': 'اختر المشغّلات لتثبيتها',
    'Choose Players to Uninstall': 'اختر المشغّلات لإزالتها',
    'Select All Players': 'تحديد جميع المشغّلات',
    'No available players to install!': 'لا توجد مشغّلات متاحة للتثبيت!',
    'No available players to uninstall!': 'لا توجد مشغّلات متاحة للإزالة!',
    'Uninstall all TMDb Helper players?': 'إزالة جميع مشغّلات TMDb Helper؟',

    # Logs
    'Log File Successfully Cleared!': 'تم مسح ملف السجل بنجاح!',
    'Error clearing Log File, see kodi.log for more info': 'خطأ في مسح ملف السجل، راجع kodi.log لمزيد من التفاصيل',
    'Cannot clear Kodi log file. Select AM Lite log file to clear.':
        'لا يمكن مسح سجل Kodi. اختر سجل AM Lite لمسحه.',
    'Log upload failed': 'فشل رفع السجل',

    # Device / QR authorization
    'Successfully Authorized!': 'تم التفويض بنجاح!',
    'Unable to start authorization. Please try again.': 'تعذّر بدء التفويض. يرجى المحاولة مرة أخرى.',
    'Authorization timed out': 'انتهت مهلة التفويض',
    'Authorization failed. Please try again.': 'فشل التفويض. يرجى المحاولة مرة أخرى.',
    'Authorization failed': 'فشل التفويض',
    'Scan QR code or visit this URL:': 'امسح رمز QR أو افتح هذا الرابط:',
    'Enter the authorization code:': 'أدخل رمز التفويض:',

    # Trakt
    'Trakt rate limit hit. Try again later.': 'تم تجاوز حد طلبات Trakt. حاول لاحقاً.',
    'Failed to retrieve Trakt account information.': 'تعذّر جلب معلومات حساب Trakt.',
    'Trakt returned an incomplete token response': 'أعاد Trakt استجابة رمز غير مكتملة',
    'Trakt authorization was declined': 'تم رفض تفويض Trakt',
    'Trakt device code is invalid or was already used': 'رمز جهاز Trakt غير صالح أو مستخدم مسبقاً',
    'No Changes Made!': 'لم يتم إجراء أي تغييرات!',
    'Changes discarded.': 'تم تجاهل التغييرات.',
    'Trakt Sync List Saved!': 'تم حفظ قائمة مزامنة Trakt!',
    'Your list has been updated![CR]Would you like to authorize Trakt and sync with supported add-ons?':
        'تم تحديث قائمتك![CR]هل تريد تفويض Trakt ومزامنته مع الإضافات المدعومة؟',
    'Your list has been updated![CR]Would you like to sync Trakt with supported add-ons?':
        'تم تحديث قائمتك![CR]هل تريد مزامنة Trakt مع الإضافات المدعومة؟',
    'Seren’s initial Trakt sync may trigger API rate limiting when multiple add-ons are syncing at the same time.[CR][CR]Continue with Seren selected?':
        'قد تتسبب المزامنة الأولى لـ Seren مع Trakt في تجاوز حد طلبات الـ API عند مزامنة عدة إضافات في الوقت نفسه.[CR][CR]المتابعة مع تحديد Seren؟',
    'Syncing more than 5 add-ons may trigger Trakt API rate limiting during the initial sync.[CR][CR]Continue with your selections?':
        'مزامنة أكثر من 5 إضافات قد تتسبب في تجاوز حد طلبات Trakt API أثناء المزامنة الأولى.[CR][CR]المتابعة مع اختياراتك؟',
    'AM Lite - Choose add-ons to sync with Trakt': 'AM Lite - اختر الإضافات لمزامنتها مع Trakt',

    # MDBList
    'API key saved': 'تم حفظ مفتاح API',
    'QR authorization missing - QR add-ons were not set up': 'تفويض QR مفقود - لم يتم إعداد إضافات QR',
    'API key missing - API key add-ons/skins were not set up': 'مفتاح API مفقود - لم يتم إعداد الإضافات/الواجهات التي تتطلبه',
    'QR authorization already active': 'تفويض QR مفعّل مسبقاً',
    'API key already configured': 'مفتاح API مُعدّ مسبقاً',
    'MDBList API key rejected': 'تم رفض مفتاح MDBList API',
    'MDBList client ID not configured': 'لم يتم إعداد معرّف عميل MDBList',
    'MDBList returned an incomplete token response': 'أعاد MDBList استجابة رمز غير مكتملة',
    'MDBList authorization was declined': 'تم رفض تفويض MDBList',
    'MDBList API Key': 'مفتاح MDBList API',
    'MDBList API Key (tip: type with the Kodi phone remote app)': 'مفتاح MDBList API (نصيحة: اكتبه عبر تطبيق ريموت Kodi على الهاتف)',
    'Missing API key': 'مفتاح API مفقود',
    'Invalid API key': 'مفتاح API غير صالح',
    'Username not returned by MDBList': 'لم يُرجع MDBList اسم المستخدم',
    'No supported add-ons or skins were detected.\nAuthorize MDBList with a QR code anyway?':
        'لم يتم اكتشاف إضافات أو واجهات مدعومة.\nتفويض MDBList برمز QR على أي حال؟',
    'QR authorization did not complete.\nContinue with the API key setup?':
        'لم يكتمل تفويض QR.\nالمتابعة مع إعداد مفتاح API؟',
    'Phone entry did not complete.\nType the key with the remote instead?':
        'لم يكتمل الإدخال عبر الهاتف.\nكتابة المفتاح باستخدام الريموت بدلاً من ذلك؟',
    'Enter on my phone (scan QR code)': 'الإدخال من هاتفي (امسح رمز QR)',
    'Enter manually (keyboard/remote)': 'الإدخال يدوياً (لوحة المفاتيح/الريموت)',
    'AM Lite - MDBList API Key': 'AM Lite - مفتاح MDBList API',
    'Choose how you would like to enter your MDBList API key:': 'اختر طريقة إدخال مفتاح MDBList API:',
    'AM Lite - MDBList Authorization': 'AM Lite - تفويض MDBList',
    'QR Code Authorization': 'التفويض برمز QR',
    'API Key Authorization': 'التفويض بمفتاح API',

    # Debrid / others
    'Real-Debrid Temporarily Down For Maintenance': 'خدمة Real-Debrid متوقفة مؤقتاً للصيانة',
    'Premiumize authorization was declined': 'تم رفض تفويض Premiumize',
    'AllDebrid returned activated but missing apikey': 'أعاد AllDebrid حالة التفعيل دون مفتاح API',
    'Offcloud is already authorized!': 'Offcloud مفوَّض مسبقاً!',
    'Enter Easynews Username:': 'أدخل اسم مستخدم Easynews:',
    'Enter Easynews Password:': 'أدخل كلمة مرور Easynews:',
    'Easynews authorization cancelled!': 'تم إلغاء تفويض Easynews!',
    'Enter EasyDebrid API Key:': 'أدخل مفتاح EasyDebrid API:',
    'EasyDebrid authorization cancelled!': 'تم إلغاء تفويض EasyDebrid!',
    'EasyDebrid authorization failed!': 'فشل تفويض EasyDebrid!',
    'EasyDebrid authorization failed! Invalid API Key.': 'فشل تفويض EasyDebrid! مفتاح API غير صالح.',

    # Phone entry (LAN page + notifications)
    'Unable to start phone entry': 'تعذّر بدء الإدخال عبر الهاتف',
    'Phone entry timed out': 'انتهت مهلة الإدخال عبر الهاتف',
    'Too many failed attempts': 'محاولات فاشلة كثيرة',
    'Not found': 'غير موجود',
    'Invalid request.': 'طلب غير صالح.',
    'Wrong code. Check the number shown on your TV.': 'رمز خاطئ. تحقق من الرقم الظاهر على التلفاز.',
    'Please enter a value.': 'يرجى إدخال قيمة.',
    'Could not verify that value. Try again.': 'تعذّر التحقق من هذه القيمة. حاول مرة أخرى.',
    'That value was rejected.': 'تم رفض هذه القيمة.',
    'Code shown on your TV': 'الرمز الظاهر على التلفاز',
    'Send to Kodi': 'إرسال إلى Kodi',
    'Need it?': 'تحتاجه؟',
    'Too many attempts. Please restart the setup on your TV.': 'محاولات كثيرة. يرجى إعادة بدء الإعداد على التلفاز.',
    'Already received. You can close this page.': 'تم الاستلام مسبقاً. يمكنك إغلاق هذه الصفحة.',
    'Locked. Restart the setup on your TV.': 'مقفل. أعد بدء الإعداد على التلفاز.',
    'Already received.': 'تم الاستلام مسبقاً.',
    'Saved! Look at your TV - you can close this page.': 'تم الحفظ! انظر إلى التلفاز - يمكنك إغلاق هذه الصفحة.',

    # Text viewer headings
    '[B]AM Lite - Supported Add-ons[/B]': '[B]AM Lite - الإضافات المدعومة[/B]',

    # Account Viewer (acctvwr)
    'View Your Authorizations': 'عرض تفويضاتك',
    'Open add-on settings menu': 'فتح قائمة إعدادات الإضافة',
    '[COLOR goldenrod]Change [COLOR gold]Scraper[/COLOR] Package[/COLOR]':
        '[COLOR goldenrod]تغيير حزمة [COLOR gold]Scrapers[/COLOR][/COLOR]',
    'Your External Provider Authorizations\n\nGears Scrapers - Not Supported\nMagento Scrapers - Not Supported':
        'تفويضات المزوّدات الخارجية\n\nGears Scrapers - غير مدعوم\nMagneto Scrapers - غير مدعوم',
    'Your External Provider Authorizations': 'تفويضات المزوّدات الخارجية',
}

# ---------------------------------------------------------------------------
# Templates for strings with dynamic parts. Captured groups are themselves run
# through tr() (so nested messages translate too) and inserted as {0}, {1}...
# ---------------------------------------------------------------------------
_P = [
    (r'(.+?) failed to install!', 'فشل تثبيت {0}!'),
    (r'(.+) Max Resolution Set!', 'تم ضبط أقصى دقة على {0}!'),
    (r'Installed (\d+) player\(s\)', 'عدد المشغّلات التي تم تثبيتها: {0}'),
    (r'Uninstalled (\d+) player\(s\)', 'عدد المشغّلات التي تمت إزالتها: {0}'),
    (r'Uninstall (\d+) selected player\(s\)\?', 'إزالة المشغّلات المحددة ({0})؟'),
    (r'No Log File Found: (.*)', 'لم يتم العثور على ملف السجل: {0}'),
    (r'Failed to view log: (.*)', 'تعذّر عرض السجل: {0}'),
    (r'Failed to upload log: (.*)', 'تعذّر رفع السجل: {0}'),
    (r'Authorize (.+)', 'تفويض {0}'),
    (r'Expires in (\d+:\d\d)', 'ينتهي خلال {0}'),
    (r'Trakt Error: (.*)', 'خطأ Trakt: {0}'),
    (r'(\d+) Years', 'سنوات: {0}'),
    (r'(\d+) days?', '{0} يوم'),
    (r'Detected (\d+) add-on\(s\) requiring QR Code authorization\.', 'عدد الإضافات التي تتطلب التفويض برمز QR: {0}'),
    (r'Detected (\d+) add-on\(s\) requiring API Key authorization\.', 'عدد الإضافات التي تتطلب التفويض بمفتاح API: {0}'),
    (r'That API key was rejected \((.*)\)\.\nTry again\?', 'تم رفض مفتاح API هذا ({0}).\nالمحاولة مرة أخرى؟'),
    (r'Request failed: (.*)', 'فشل الطلب: {0}'),
    (r'EasyDebrid authorization failed! HTTP (.*)', 'فشل تفويض EasyDebrid! HTTP {0}'),
    (r'Real-Debrid Auth revoked due to:\s+(.*)', 'تم إلغاء تفويض Real-Debrid بسبب: {0}'),
    (r'Offcloud authorization failed: (.*)', 'فشل تفويض Offcloud: {0}'),
    (r'AllDebrid PIN error: (.*)', 'خطأ رمز AllDebrid: {0}'),
    (r'Send (.+) to Kodi', 'إرسال {0} إلى Kodi'),
    (r'Email: (.*)', 'البريد الإلكتروني: {0}'),
    (r'Account ID: (.*)', 'معرّف الحساب: {0}'),
    (r'Status: (.*)', 'الحالة: {0}'),
    (r'Expires: (.*)', 'ينتهي في: {0}'),
    (r'\[B\]AM Lite -  v(.+?) - ChangeLog\[/B\]', '[B]AM Lite - الإصدار {0} - سجل التغييرات[/B]'),
    (r'\[B\]AM Lite -  v(.+?) - Torbox & OffCloud Auth Help\[/B\]', '[B]AM Lite - الإصدار {0} - مساعدة تفويض TorBox و OffCloud[/B]'),
    (r'\[B\]AM Lite -  v(.+?) - Restore to Default\[/B\]', '[B]AM Lite - الإصدار {0} - الاستعادة للوضع الافتراضي[/B]'),
    (r'\[B\]AM Lite -  v(.+?) - (.+)\[/B\]', '[B]AM Lite - الإصدار {0} - {1}[/B]'),
    (r'\[B\]Account Manager Lite - (.+)\[/B\]', '[B]Account Manager Lite - {0}[/B]'),
    # Account Viewer
    (r'(.+) - \[COLOR red\]Not Authorized\[/COLOR\]', '{0} - [COLOR red]غير مفوَّض[/COLOR]'),
    (r'(.+) - \[COLOR springgreen\]Authorized\[/COLOR\]', '{0} - [COLOR springgreen]مفوَّض[/COLOR]'),
    (r'(.+) - \[COLOR red\]No Scraper Synced\[/COLOR\]', '{0} - [COLOR red]لا توجد Scrapers متزامنة[/COLOR]'),
    (r'(.+) - \[COLOR springgreen\](.+) Scrapers Synced\[/COLOR\]', '{0} - [COLOR springgreen]تمت مزامنة {1} Scrapers[/COLOR]'),
    (r'\[COLOR blue\]Open \[COLOR dodgerblue\](.+)\[/COLOR\] Settings\[/COLOR\]',
        '[COLOR blue]فتح إعدادات [COLOR dodgerblue]{0}[/COLOR][/COLOR]'),
    (r'\[COLOR gray\](.+) Settings\[/COLOR\]', '[COLOR gray]إعدادات {0}[/COLOR]'),
    (r'Your (.+) Authorizations', 'تفويضات {0}'),
    (r'(.+) Revoked!', 'تم إلغاء تفويض {0}!'),
]
PATTERNS = [(re.compile('^' + rx + '$', re.S), tpl) for rx, tpl in _P]


def tr(text):
    """Return Arabic for a known English UI string, otherwise the input unchanged."""
    if not isinstance(text, str) or not text or not is_arabic():
        return text
    hit = EXACT.get(text)
    if hit is not None:
        return hit
    for rx, tpl in PATTERNS:
        m = rx.match(text)
        if m:
            return tpl.format(*[tr(g) if g else g for g in m.groups()])
    return text


def tr_list(items):
    return [tr(i) if isinstance(i, str) else i for i in items]


# ---------------------------------------------------------------------------
# Drop-in wrappers for xbmcgui dialogs that translate their text arguments
# ---------------------------------------------------------------------------
_SKIP_KW = {'defaultt', 'default', 'icon', 'type', 'option', 'autoclose',
            'preselect', 'useDetails', 'sound', 'time', 'customlabel_default'}


def _t_arg(value):
    if isinstance(value, str):
        return tr(value)
    if isinstance(value, (list, tuple)):
        return type(value)(tr(v) if isinstance(v, str) else v for v in value)
    return value


class _Translating(object):
    _METHODS = ()

    def __init__(self, obj):
        object.__setattr__(self, '_obj', obj)

    def __getattr__(self, name):
        attr = getattr(self._obj, name)
        if name in self._METHODS and callable(attr):
            def wrapper(*args, **kwargs):
                args = [_t_arg(a) for a in args]
                kwargs = dict((k, v if k in _SKIP_KW else _t_arg(v)) for k, v in kwargs.items())
                return attr(*args, **kwargs)
            return wrapper
        return attr


class _DialogProxy(_Translating):
    _METHODS = ('ok', 'yesno', 'yesnocustom', 'select', 'multiselect', 'contextmenu',
                'notification', 'textviewer', 'input', 'numeric', 'browse',
                'browseSingle', 'browseMultiple')


class _ProgressProxy(_Translating):
    _METHODS = ('create', 'update')


def Dialog():
    return _DialogProxy(xbmcgui.Dialog())


def DialogProgress():
    return _ProgressProxy(xbmcgui.DialogProgress())


def DialogProgressBG():
    return _ProgressProxy(xbmcgui.DialogProgressBG())


def apply_window_labels(window, keys):
    """Expose static XML labels as window properties (am.l.<n>) so they follow tr()."""
    for idx, text in enumerate(keys):
        try:
            window.setProperty('am.l.%d' % idx, tr(text))
        except Exception:
            pass
    try:
        window.setProperty('am.rtl', 'true' if is_arabic() else '')
    except Exception:
        pass
