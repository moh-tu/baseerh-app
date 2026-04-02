import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import sqlite3
import hashlib
from datetime import date
import pandas as pd
from PIL import Image
import smtplib
import random
from email.mime.text import MIMEText

st.set_page_config(page_title="بصيرة | خبير المناقصات", layout="wide")

st.markdown("""
<style>
    /* 1. استيراد الخط وتنسيق النص العام */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Cairo', sans-serif;
        direction: RTL;
        text-align: right;
    }

    /* 2. الإخفاء المطلق للسايدبار والهيدر الافتراضي */
    section[data-testid="stSidebar"], 
    div[data-testid="stSidebarNav"],
    header[data-testid="stHeader"],
    .st-emotion-cache-6q9sum,
    .st-emotion-cache-16idsys {
        display: none !important;
        width: 0px !important;
        position: fixed !important;
        left: -1000px !important;
    }

    /* 3. إلغاء الهوامش وإجبار المحتوى على أخذ كامل العرض */
    .main .block-container {
        max-width: 100% !important;
        width: 100% !important;
        padding: 2rem 5% !important;
        margin: 0px !important;
    }

    /* 4. تصميم القائمة العائمة (تظهر فوق كل شيء) */
    ..floating-nav {
    position: fixed;
    top: 0;
    right: -400px; /* مخفية */
    width: 350px;
    height: 100vh;
    background-color: #161b22;
    transition: 0.3s ease;
    z-index: 999999 !important;
}

.floating-nav.active {
    right: 0; /* تظهر */
}

    /* 5. تنسيق كروت النتائج والتبويبات */
    .result-card {
        background: #1c2128;
        border-radius: 12px;
        border: 1px solid #30363d;
        padding: 25px;
        margin-top: 15px;
        border-right: 6px solid #007BFF;
        color: #adbac7;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1c2128;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007BFF !important;
    }

    /* تحسين شكل الأزرار داخل القائمة */
    .floating-nav button {
        margin-bottom: 10px !important;
    }
</style>
""", unsafe_allow_html=True)
# --- تحميل اللوقو ---
# --- تحميل اللوقو ---
def send_verification_code(email, code):
    sender_email = "m74md44@gmail.com"
    sender_password = "kudqenkcbixrvedl"

    msg = MIMEText(f"رمز التحقق الخاص بك هو: {code}")
    msg['Subject'] = "Verification Code"
    msg['From'] = sender_email
    msg['To'] = email

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False
logo = Image.open("logo1.png.png")
# --- 1. إعداد قاعدة البيانات ---
conn = sqlite3.connect('tender_ultimate_2026.db', check_same_thread=False)
c = conn.cursor()
try:
    c.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
except sqlite3.OperationalError:
    # العمود موجود مسبقًا، تجاهل الخطأ
    pass
conn.commit()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, email TEXT UNIQUE, password TEXT, is_paid INTEGER DEFAULT 0, 
              api_key TEXT DEFAULT '', daily_limit INTEGER DEFAULT 5, usages_today INTEGER DEFAULT 0, last_use TEXT)''')
conn.commit()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 2. محرك المعالجة والذكاء الاصطناعي المتطور ---
def get_rag_response(query, context_text, media_files, model):
    # تجهيز قائمة المحتويات لـ Gemini (نصوص + وسائط)
    content_list = [f"أنت خبير مناقصات ومستشار عقاري سعودي. بناءً على البيانات المرفقة (نصوص/صور/فيديو)، أجب بدقة: {query}\n\nالسياق النصي:\n{context_text}"]
    
    # إضافة الملفات البصرية للقائمة إذا وجدت
    if media_files:
        for file in media_files:
            file_ext = file.name.split('.')[-1].lower()
            if file_ext in ['jpg', 'jpeg', 'png']:
                img = Image.open(file)
                content_list.append(img)
            elif file_ext in ['mp4', 'mov']:
                # تمرير ملف الفيديو مباشرة لموديل Gemini
                content_list.append(file)
    
    response = model.generate_content(content_list)
    return response.text

# دالة معالجة الاختيارات الموحدة (تم تحديثها لدعم الوسائط)
def process_selection(selected, u_info, model, key_suffix):
    if selected != "إختر..." and st.button(f"بدء استخراج {selected} ✨", key=f"btn_{key_suffix}_{selected}"):
        if u_info[3] < u_info[2]:
            with st.spinner(f"جاري تحليل {selected}..."):
                # تجميع النصوص من جميع الملفات النصية المرفوعة
                all_context = "\n".join(st.session_state.get('extracted_text', []))[:400000]
                
                # استدعاء البرومبت المناسب (نفس برومبتاتك السابقة)
                if selected == "مصفوفة المخاطر":
                    q = "أنشئ مصفوفة مخاطر بجدول احترافي يتضمن: بنود الغرامات، شروط الضمان البنكي، ومواعيد التسليم النهائية."
                elif selected == "مطابقة التصنيف والدرجة المطلوبة":
                    q = "بناءً على حجم وتفاصيل المناقصة، ما هي درجة التصنيف المطلوبة للمقاول حسب نظام تصنيف المقاولين السعودي الجديد؟"
                elif selected == "المخطط الزمني التقديري (Gantt Chart)":
                    q = "بناءً على نطاق العمل ومدة المشروع المذكورة، قم بتوليد جدول زمني تقديري لمراحل التنفيذ في شكل جدول."
                elif selected == "مدقق عقود إيجار (مطابقة نظام الوساطة)":
                    q = "أنت مستشار قانوني عقاري خبير بنظام الوساطة السعودي. قم بفحص العقد المرفق والتحقق من بيانات الوسيط والعمولة (2.5%) وبيانات العقار."
                elif selected == "مطابقة كود البناء السعودي (SBC)":
                    q = "بصفتك مهندساً استشارياً، فحص المخططات/المواصفات ومطابقتها مع SBC 201, 301, 601, 801. حدد حالة المطابقة ومرجع الكود."
                elif selected == "محلل فواتير الصيانة (Benchmark)":
                    q = "قارن أسعار الفاتورة المرفقة بأسعار السوق السعودي الحالي (التكييف، السباكة، إلخ) وحدد الهدر والتوصية النهائية."
                elif selected == "فرص نمو العقار والمشاريع الكبرى":
                    q = "حلل موقع العقار وقربه من مشاريع رؤية 2030 (نيوم، القدية، إلخ) وتأثيرها على نمو القيمة الرأسمالية."
                elif selected == "كاشف الثغرات القانونية ":
                    q = "قم بمسح الكراسة للكشف عن 'الألغام القانونية' وثغرات أوامر التغيير واختلال التوازن التعاقدي."
                elif selected == "تحليل اتجاهات السوق(Market Trends)":
                    q = "قارن سعر المتر في المشروع بمتوسط أسعار الحي في البورصة العقارية ومؤشر إيجار."
                elif selected == "التقرير التنفيذي (Go/No-Go)":
                    q = "صغ ملخص قرار نهائي (Go/No-Go) يوضح المكاسب والتحديات والجدوى المالية في صفحة واحدة."
                elif selected == "مولد اعلانات واتساب وحراج وتويتر ":
                    q = "صغ محتوى إعلاني جذاب للواتساب، X، ومنصة سهل مع الالتزام بضوابط الهيئة العامة للعقار."
                elif selected == "صانع محتوى TikTok (سيناريو سريع) احترافي جدا":
                    q = "اكتب سيناريو تيك توك احترافي (Hook, Body, CTA) مع توجيهات بصرية وموسيقى ترند."
                elif selected == "صانع محتوى TikTok (سيناريو سريع)":
                    q = "اكتب سيناريو تيك توك يعتمد على 'تصوير الجوال' فقط (POV) بلهجة بيضاء سعودية جذابة."
                elif selected == "استخراج وتحليل جداول الكميات (BOQ)":
                    q = "ابحث عن جداول الكميات واستخرج البنود والكميات مع تحليل مخاطر تسعيرها."
                else:
                    q = f"استخرج تفاصيل {selected} من الملفات المرفقة بشكل منظم."
                
                # إرسال الطلب للموديل مع تمرير الوسائط المرفوعة
                res = get_rag_response(q, all_context, st.session_state.get('media_files', []), model)
                st.markdown(f"<div class='result-card'>{res}</div>", unsafe_allow_html=True)
                
                c.execute('UPDATE users SET usages_today = usages_today + 1 WHERE username=?', (st.session_state['username'],))
                conn.commit()
        else:
            st.error("🚫 عذراً، لقد انتهت محاولاتك لليوم.")

# --- 3. التنسيق والخطوط ---



# --- 4. إدارة الجلسة والدخول ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'extracted_text' not in st.session_state: st.session_state['extracted_text'] = []
if 'media_files' not in st.session_state: st.session_state['media_files'] = []

def auth_page():
    try:
        st.image("logo1.png.png", width=120)
    except:
        st.warning("⚠️ ملف اللوجو مفقود")

    st.markdown("<h1 class='main-title'>🏛️ منصة خبير العقار الألي</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب"])
    
    with t1:
        # 1. إدخال البريد أولاً لإرسال الكود
        login_email = st.text_input("البريد الإلكتروني المسجل", key="login_email_input")
        
        if login_email and st.button("إرسال رمز التحقق للدخول"):
            code = str(random.randint(100000, 999999))
            if send_verification_code(login_email, code):
                st.success(f"تم إرسال الرمز إلى {login_email}")
                st.session_state['verification_code'] = code
            else:
                st.error("فشل إرسال الإيميل، تأكد من صحته")
        
        # 2. خانات الدخول
        input_code = st.text_input("أدخل رمز التحقق المستلم", key="login_code_input")
        u = st.text_input("اسم المستخدم", key="login_user_input")
        p = st.text_input("كلمة المرور", type="password", key="login_pass_input")
        
        if st.button("تأكيد الدخول"):
            # التحقق من الرمز أولاً
            if 'verification_code' in st.session_state and input_code == st.session_state['verification_code']:
                # التحقق من قاعدة البيانات
                c.execute('SELECT * FROM users WHERE username =? AND password =?', (u, make_hashes(p)))
                data = c.fetchone()
                if data:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = data[0]
                    st.success("تم الدخول بنجاح!")
                    st.rerun()
                else: 
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
            else:
                st.error("رمز التحقق غير صحيح أو لم يتم طلبه")

    with t2:
        ne = st.text_input("البريد الالكتروني الجديد", key="reg_email")
        nu = st.text_input("اسم المستخدم الجديد", key="reg_user")
        np = st.text_input("كلمة المرور الجديدة", type="password", key="reg_pass")
        
        if st.button("إنشاء الحساب"):
            if ne and nu and np:
                try:
                    # إضافة المستخدم الجديد مع القيم الافتراضية
                    c.execute('''INSERT INTO users(email, username, password, is_paid, api_key, daily_limit, usages_today, last_use) 
                                 VALUES (?,?,?, 1, 'YOUR_FREE_KEY', 5, 0, ?)''', 
                              (ne, nu, make_hashes(np), str(date.today())))
                    conn.commit()
                    st.success("🎉 تم إنشاء الحساب بنجاح! اهلا بك في بصيره.")
                except sqlite3.IntegrityError:
                    st.error("⚠️ هذا المستخدم أو البريد مسجل مسبقاً.")
            else:
                st.warning("الرجاء تعبئة جميع الخانات")
def app_interface():
    # 1. جلب بيانات المستخدم من قاعدة البيانات
    c.execute('SELECT is_paid, api_key, daily_limit, usages_today FROM users WHERE username=?', (st.session_state['username'],))
    u_info = c.fetchone()
    
    # 1. التحقق من بيانات المستخدم (لضمان الأمان وعدم تعطل التطبيق)
    # 1. التحقق من بيانات المستخدم
    # 1. التحقق من بيانات المستخدم (لضمان الأمان وعدم تعطل التطبيق)
    # 1. التحقق من بيانات المستخدم
    if not u_info:
        st.error("تعذر جلب بيانات المستخدم.")
        return

    # 2. إدارة حالة القائمة المنسدلة (Overlay)
    if 'menu_active' not in st.session_state:
        st.session_state.menu_active = False

    # التعديل الجديد: تحديد الكلاس ديناميكياً
    menu_class = "floating-nav active" if st.session_state.menu_active else "floating-nav"

    # 3. الهيدر الرئيسي (اللوجو والترحيب)
    st.markdown('<div style="text-align:center; padding-bottom:15px;">', unsafe_allow_html=True)
    try:
        st.image("logo1.png.png", width=110) 
    except:
        pass
    st.markdown(f"<h2 style='margin:0; color:white;'>بصيرة 🔎</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#007BFF; font-weight:bold; margin-top:5px;'>أهلاً بك، {st.session_state['username']}</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. زر فتح المنيو
    col_menu, _ = st.columns([1, 8])
    with col_menu:
        if st.button("☰ القائمة", use_container_width=True):
            st.session_state.menu_active = True
            st.rerun()

    # 5. منطق القائمة العائمة باستخدام الكلاس المطور
    st.markdown(f'<div class="{menu_class}">', unsafe_allow_html=True)
    
    # محتويات القائمة تظهر فقط عند التفعيل
    if st.session_state.menu_active:
        if st.button("❌ إغلاق القائمة", key="close_overlay", use_container_width=True):
            st.session_state.menu_active = False
            st.rerun()
        
        st.markdown("<br><h3 style='text-align: center; color: white;'>التنقل السريع</h3>", unsafe_allow_html=True)
        st.divider()
        
        # خيارات التنقل
        nav_items = ["🔍 التحليل الذكي", "💳 باقتي", "⚙️ الإدارة"]
        active_items = nav_items if st.session_state['username'] == "mohammed.admin" else nav_items[:2]
        
        for item in active_items:
            if st.button(item, key=f"btn_{item}", use_container_width=True):
                st.session_state.last_choice = item
                st.session_state.menu_active = False
                st.rerun()
        
        st.divider()
        if st.button("🚪 تسجيل الخروج", key="logout_sidebar", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

    # 6. تحديد الصفحة النشطة لعرض محتواها
    choice = st.session_state.get('last_choice', "🔍 التحليل الذكي")
    
    # --- هنا يبدأ محتوى الصفحات (if choice == "🔍 التحليل الذكي" ... إلخ) ---
        # هنا يكمل باقي كود استخراج وتحليل البيانات (السطر 263 وما بعده)
    # بقية الكود كما هو...

    if choice == "🔍 التحليل الذكي":
        st.markdown("<h2 class='main-title'>🔍 استخراج وتحليل بيانات المناقصة</h2>", unsafe_allow_html=True)
        
        if u_info[0] == 1:
            uploaded_files = st.file_uploader("(Excel),(Photo),(Video),(pdf) ارفق ملفات المشروع", 
                                             type=['pdf', 'xlsx', 'jpg', 'png', 'mp4', 'mov'], 
                                             accept_multiple_files=True)
            
            if uploaded_files:
                st.session_state['extracted_text'] = []
                st.session_state['media_files'] = []
                
                # تجهيز موديل Gemini
                genai.configure(api_key=u_info[1])
                model = genai.GenerativeModel('gemini-3-flash-preview')

                # حلقة تكرار لمعالجة كل ملف حسب نوعه
                for file in uploaded_files:
                    ext = file.name.split('.')[-1].lower()
                    
                    if ext == 'pdf':
                        try:
                            reader = PdfReader(file)
                            text = "".join([page.extract_text() for page in reader.pages])
                            st.session_state['extracted_text'].append(text)
                            st.success(f"✅ تم قراءة PDF: {file.name}")
                        except: st.error(f"❌ خطأ في PDF: {file.name}")
                        
                    elif ext == 'xlsx':
                        df = pd.read_excel(file)
                        st.session_state['extracted_text'].append(df.to_string())
                        st.success(f"✅ تم قراءة Excel: {file.name}")
                        
                    elif ext in ['jpg', 'png', 'jpeg', 'mp4', 'mov']:
                        st.session_state['media_files'].append(file)
                        if ext in ['mp4', 'mov']:
                            st.info(f"📽️ فيديو جاهز للتحليل: {file.name}")
                        else:
                            st.info(f"🖼️ صورة جاهزة للتحليل: {file.name}")

                # --- التبويبات الأربعة (خارج شروط المعالجة لتبقى ظاهرة) ---
                st.divider()
                t1, t2, t3, t4 = st.tabs(["🎯 تحليل المناقصات", "⚖️ الإدارة والامتثال", "🛡️ المخاطر والقرار", "📢 التسويق الذكي"])

                with t1:
                    opt1 = ["مطابقة كود البناء السعودي","مطابقة التصنيف والدرجه المطلوبه","المخطط الزمني التقديري", "ملخص المشروع", "نطاق العمل", "الشروط الفنية", "استخراج وتحليل جداول الكميات (BOQ)"]
                    sel1 = st.selectbox("بند التحليل:", ["إختر..."] + opt1, key="s1")
                    process_selection(sel1, u_info, model, "t1")

                with t2:
                    opt2 = ["كاشف الثغرات القانونية","فرص نمو العقار والمشاريع الكبرى","محلل فواتير الصيانه (Benchmarks)","مدقق عقود إيجار (مطابقة نظام الوساطة)","الشروط المالية", "المواعيد النهائية"]
                    sel2 = st.selectbox("بند الامتثال:", ["إختر..."] + opt2, key="s2")
                    process_selection(sel2, u_info, model, "t2")

                with t3:
                    opt3 = ["التقرير التنفيذي (Go/No-Go)","تحليل اتجاهات السوق(Market Trends)","مصفوفة المخاطر", "المخاطر القانونية", "الضمانات المطلوبة", "أسباب استبعاد العروض", "الغرامات"]
                    sel3 = st.selectbox("بند المخاطر:", ["إختر..."] + opt3, key="s3")
                    process_selection(sel3, u_info, model, "t3")

                with t4:
                    opt4 = ["صانع محتوى TikTok (سيناريو سريع) احترافي جدا","صانع محتوى TikTok (سيناريو سريع)","مولد اعلانات واتساب وحراج وتويتر","نصائح للفوز"]
                    sel4 = st.selectbox("خيار التسويق الحالي:", ["إختر..."] + opt4, key="s4")
                    process_selection(sel4, u_info, model, "t4")

                st.divider()
                q_free = st.text_input("💡 سؤال حر عن الملفات المرفوعة:")
                if q_free and st.button("اسأل"):
                    res_free = get_rag_response(q_free, "\n".join(st.session_state['extracted_text']), st.session_state['media_files'], model)
                    st.markdown(f"<div class='result-card'>{res_free}</div>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ حسابك غير مفعل حالياً. يرجى التواصل مع الإدارة.")

    elif choice == "💳 باقتي":
        st.markdown("<h2 class='main-title'>💳 معلومات الاشتراك</h2>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='result-card'>
            <h3 style='text-align: center; color: #007BFF;'>حالة الحساب</h3>
            <hr style='border: 0.5px solid #30363d;'>
            <p><b>👤 المستخدم:</b> {st.session_state['username']}</p>
            <p><b>📊 الاستهلاك اليومي:</b> {u_info[3]} من {u_info[2]}</p>
            <p><b>✨ نوع الباقة:</b> {'حساب مفعل' if u_info[0] == 1 else 'حساب تجريبي'}</p>
            <hr style='border: 0.5px solid #30363d;'>
            <p style='font-size: 0.9em; color: #8b949e;'>يتم الآن تحليل النصوص والصور والفيديو معاً في هذه النسخة المحدثة.</p>
        </div>
        """, unsafe_allow_html=True)

    elif choice == "⚙️ الإدارة":
        st.markdown("<h2 style='text-align: center; color: #007BFF;'>⚙️ لوحة التحكم بالمستخدمين</h2>", unsafe_allow_html=True)
        
        # جلب قائمة المستخدمين
        c.execute('SELECT username, is_paid, api_key, daily_limit FROM users')
        users_list = c.fetchall()
        
        if not users_list:
            st.info("لا يوجد مستخدمين مسجلين حالياً.")
        
        for user in users_list:
            # استخدام عنوان نظيف للـ Expander لمنع تداخل النصوص
            with st.expander(f"👤 إدارة حساب: {user[0]}"):
                st.markdown(f"**بيانات المستخدم:** `{user[0]}`")
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    # تفعيل الاشتراك
                    active_status = bool(user[1])
                    new_active = st.checkbox("تفعيل الحساب", value=active_status, key=f"active_{user[0]}")
                    
                    # تعديل الحد اليومي
                    new_limit = st.number_input("الحد اليومي للاستخدام", value=user[3], min_value=0, key=f"limit_{user[0]}")
                
                with col2:
                    # تعديل مفتاح الـ API
                    new_key = st.text_input("Gemini API Key", value=user[2], type="password", key=f"api_{user[0]}")
                
                # زر الحفظ لكل مستخدم بشكل مستقل
                if st.button(f"حفظ تعديلات {user[0]}", key=f"save_btn_{user[0]}", use_container_width=True):
                    c.execute('UPDATE users SET is_paid=?, api_key=?, daily_limit=? WHERE username=?', 
                              (int(new_active), new_key, new_limit, user[0]))
                    conn.commit()
                    st.success(f"✅ تم تحديث بيانات {user[0]} بنجاح!")
                    st.rerun()

def main():
    if not st.session_state['logged_in']:
        auth_page()
    else:
        app_interface()

if __name__ == '__main__':
    main()