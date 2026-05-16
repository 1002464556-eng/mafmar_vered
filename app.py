
import streamlit as st
import pandas as pd
import numpy as np
import os

# ==================== הגדרות תצוגה עיצוביות - רמת Top 1% (2026 Style) ====================
st.set_page_config(page_title="דשבורד מפמ\"ר לאומי", layout="wide", page_icon="🌐")

# הזרקת עיצוב מותאם אישית למראה נקי, עתידני ומניעת חיתוך נתונים בטבלאות
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Assistant', sans-serif;
        background-color: #f8fafc;
        direction: rtl;
        text-align: right;
    }
    * { direction: rtl; }
    
    /* כותרת עליונה חדישה בסגנון Glassmorphism */
    .dashboard-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 30px;
        border-radius: 16px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
        margin-bottom: 35px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .dashboard-header h1 {
        color: #ffffff !important;
        font-weight: 800;
        font-size: 2.6rem;
        margin: 0;
        text-align: center;
    }
    .dashboard-header p {
        color: #94a3b8;
        font-size: 1.15rem;
        margin-top: 8px;
        text-align: center;
    }
    
    /* כרטיסיות מדדים פרימיום */
    .custom-card {
        background: white;
        border-radius: 14px;
        padding: 22px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
        border: 1px solid #e2e8f0;
        position: relative;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .custom-card::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 6px;
        height: 100%;
    }
    .card-math::before { background: #f43f5e; } /* ורוד-אדום אלגנטי למתמטיקה */
    .card-sci::before { background: #0ea5e9; }  /* כחול טכנולוגי למדעים */
    
    .card-label { font-size: 0.95rem; color: #64748b; font-weight: 600; margin-bottom: 6px; }
    .card-value { font-size: 2.3rem; color: #0f172a; font-weight: 800; line-height: 1; }
    .card-subtext { font-size: 0.88rem; color: #94a3b8; margin-top: 8px; }
    
    /* יישור תיבות בחירה לרשות המשתמש */
    div[data-baseweb="select"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* מניעת חיתוך של שמות בתי ספר בטבלה */
    .stDataFrame div table {
        direction: rtl !important;
        text-align: right !important;
    }
    .stDataFrame td, .stDataFrame th {
        white-space: normal !important;
        word-break: keep-all !important;
        font-size: 14.5px !important;
    }
</style>
""", unsafe_allow_html=True)

# הצגת באנר הכותרת המעוצב
st.markdown("""
<div class="dashboard-header">
    <h1>🌐 מערכת ניטור לאומית - משימות מפמ"ר</h1>
    <p>ממשק ניהול סינכרוני משולב | מתמטיקה ומדעים</p>
</div>
""", unsafe_allow_html=True)

# ==================== מנוע ניקוי ועיבוד נתונים מאובטח ====================
def clean_numeric(val):
    if pd.isna(val): return 0
    val_str = str(val).replace(',', '').replace('%', '').strip()
    try:
        return int(float(val_str))
    except:
        return 0

def process_subject_file(file_path, subject_name):
    """קריאה, ניקוי, ושקלול אבסולוטי של קובץ מקצועי בודד"""
    if not file_path or not os.path.exists(file_path):
        return pd.DataFrame()
        
    try:
        if file_path.endswith('.csv'):
            try: df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            except: df = pd.read_csv(file_path, encoding='cp1255', dtype=str)
        else:
            df = pd.read_excel(file_path, dtype=str)
    except:
        return pd.DataFrame()
        
    df.columns = [str(c).strip() for c in df.columns]
    
    # סינון שורות סיכום כלליות שעלולות לעוות את הנתונים
    if 'מוסד' not in df.columns:
        return pd.DataFrame()
        
    df = df[~df['מוסad'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False) if 'מוסad' in df.columns else ~df['מוסד'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False)]
    df = df[df['מוסד'].notna() & (df['מוסד'].astype(str).str.strip() != '')]
    
    # זיהוי עמודות פוטנציאל וביצוע
    pot_col = next((c for c in df.columns if 'פוטנציאל' in c), None)
    done_col = next((c for c in df.columns if 'שביצעו משימה אחת' in c and 'אחוז' not in c), None)
    if not done_col:
        done_col = next((c for c in df.columns if 'שביצעו' in c and 'אחוז' not in c), None)
        
    df['raw_pot'] = df[pot_col].apply(clean_numeric) if pot_col else 0
    df['raw_done'] = df[done_col].apply(clean_numeric) if done_col else 0
    
    # חילוץ עמודות שיוך ארגוני
    dist_col = next((c for c in df.columns if 'מחוז' in c), 'מחוז')
    sup_col = next((c for c in df.columns if 'מפקח' in c), 'מפקח')
    auth_col = next((c for c in df.columns if 'רשות' in c), 'רשות')
    
    df['clean_dist'] = df[dist_col].fillna('לא ידוע').astype(str).str.strip() if dist_col in df.columns else 'לא ידוע'
    df['clean_sup'] = df[sup_col].fillna('לא ידוע').astype(str).str.strip() if sup_col in df.columns else 'לא ידוע'
    df['clean_auth'] = df[auth_col].fillna('-').astype(str).str.strip() if auth_col in df.columns else '-'
    
    # קיבוץ ברמת מוסד (איחוד כיתות שונות בתוך אותו בית ספר)
    grouped = df.groupby('מוסד').agg({
        'clean_dist': 'first',
        'clean_sup': 'first',
        'clean_auth': 'first',
        'raw_pot': 'sum',
        'raw_done': 'sum'
    }).reset_index()
    
    # יצירת מבנה עמודות סטנדרטי למניעת KeyErrors
    grouped[f'פוטנציאל {subject_name}'] = grouped['raw_pot']
    grouped[f'ביצעו {subject_name}'] = grouped['raw_done']
    grouped[f'אחוז {subject_name}'] = np.where(
        grouped['raw_pot'] > 0,
        (grouped['raw_done'] / grouped['raw_pot']) * 100.0,
        0.0
    )
    
    return grouped[['מוסד', 'clean_dist', 'clean_sup', 'clean_auth', f'פוטנציאל {subject_name}', f'ביצעו {subject_name}', f'אחוז {subject_name}']]

@st.cache_data(ttl=600)
def load_and_merge_data():
    """סריקת התיקייה, טעינת שני הקבצים בנפרד וביצוע מיזוג מושלם"""
    files = os.listdir('.')
    
    math_file = next((f for f in files if 'מתמטיק' in f and (f.endswith('.csv') or f.endswith('.xlsx'))), None)
    sci_file = next((f for f in files if 'מדע' in f and (f.endswith('.csv') or f.endswith('.xlsx'))), None)
    
    df_math = process_subject_file(math_file, 'מתמטיקה')
    df_sci = process_subject_file(sci_file, 'מדעים')
    
    if df_math.empty and df_sci.empty:
        return pd.DataFrame(), "לא נמצאו קבצי נתונים תקינים בתיקיית ה-GitHub."
        
    # מיזוג מושלם (Full Outer Join) כדי שמוסד לא יימחק גם אם הוא קיים רק בקובץ אחד
    if not df_math.empty and not df_sci.empty:
        df_merged = pd.merge(df_math, df_sci, on='מוסד', how='outer', suffixes=('_math', '_sci'))
        
        # איחוד עמודות המטה-דאטה משני הקבצים במקרה של חוסרים
        df_merged['מחוז'] = df_merged['clean_dist_math'].combine_first(df_merged['clean_dist_sci']).fillna('לא ידוע')
        df_merged['מפקח'] = df_merged['clean_sup_math'].combine_first(df_merged['clean_sup_sci']).fillna('לא ידוע')
        df_merged['רשות'] = df_merged['clean_auth_math'].combine_first(df_merged['clean_auth_sci']).fillna('-')
        
        # הסרת עמודות זמניות
        df_merged.drop(columns=['clean_dist_math', 'clean_dist_sci', 'clean_sup_math', 'clean_sup_sci', 'clean_auth_math', 'clean_auth_sci'], errors='ignore', inplace=True)
    elif not df_math.empty:
        df_merged = df_math.copy()
        df_merged.rename(columns={'clean_dist': 'מחוז', 'clean_sup': 'מפקח', 'clean_auth': 'רשות'}, inplace=True)
        df_merged['פוטנציאל מדעים'] = 0
        df_merged['ביצעו מדעים'] = 0
        df_merged['אחוז מדעים'] = np.nan
    else:
        df_merged = df_sci.copy()
        df_merged.rename(columns={'clean_dist': 'מחוז', 'clean_sup': 'מפקח', 'clean_auth': 'רשות'}, inplace=True)
        df_merged['פוטנציאל מתמטיקה'] = 0
        df_merged['ביצעו מתמטיקה'] = 0
        df_merged['אחוז מתמטיקה'] = np.nan
        
    # טיפול אחיד בערכי קצה וחסרים
    df_merged['פוטנציאל מתמטיקה'] = df_merged['פוטנציאל מתמטיקה'].fillna(0).astype(int)
    df_merged['ביצעו מתמטיקה'] = df_merged['ביצעו מתמטיקה'].fillna(0).astype(int)
    df_merged['אחוז מתמטיקה'] = df_merged['אחוז מתמטיקה'].fillna(np.nan)
    
    df_merged['פוטנציאל מדעים'] = df_merged['פוטנציאל מדעים'].fillna(0).astype(int)
    df_merged['ביצעו מדעים'] = df_merged['ביצעו מדעים'].fillna(0).astype(int)
    df_merged['אחוז מדעים'] = df_merged['אחוז מדעים'].fillna(np.nan)
    
    return df_merged, None

# ==================== הרצת תהליך עיבוד הנתונים המרכזי ====================
df_main, error_msg = load_and_merge_data()

if error_msg:
    st.error(f"⚠️ {error_msg}")
    st.stop()

# ==================== חלק א': סינון מחוזי ומדדי על משוקללים ====================
districts = sorted([d for d in df_main['מחוז'].unique() if d != 'לא ידוע'])

if districts:
    selected_district = st.selectbox("🎯 בחר מחוז לצפייה:", districts)
    df_dist = df_main[df_main['מחוז'] == selected_district]
    
    # חישוב ממוצע אמת מחוזי (סך תלמידים שביצעו חלקי סך פוטנציאל במחוז)
    dist_pot_math = df_dist['פוטנציאל מתמטיקה'].sum()
    dist_done_math = df_dist['ביצעו מתמטיקה'].sum()
    dist_avg_math = (dist_done_math / dist_pot_math * 100) if dist_pot_math > 0 else 0.0
    
    dist_pot_sci = df_dist['פוטנציאל מדעים'].sum()
    dist_done_sci = df_dist['ביצעו מדעים'].sum()
    dist_avg_sci = (dist_done_sci / dist_pot_sci * 100) if dist_pot_sci > 0 else 0.0
    
    st.markdown(f"<h3 style='color:#0f172a; margin-top:5px; font-weight:700;'>תמונת מצב - מחוז {selected_district}</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="custom-card card-math">
            <div class="card-label">📐 שקלול מחוזי - מתמטיקה</div>
            <div class="card-value">{dist_avg_math:.1f}%</div>
            <div class="card-subtext">פוטנציאל תלמידים כולל: <b>{int(dist_pot_math):,}</b></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="custom-card card-sci">
            <div class="card-label">🔬 שקלול מחוזי - מדעים</div>
            <div class="card-value">{dist_avg_sci:.1f}%</div>
            <div class="card-subtext">פוטנציאל תלמידים כולל: <b>{int(dist_pot_sci):,}</b></div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("<br>", unsafe_allow_html=True)
    
    # ==================== חלק ב': פילוח מפקחים וטבלת רמזור חכמה ====================
    sups = sorted([s for s in df_dist['מפקח'].unique() if s != 'לא ידוע'])
    
    if sups:
        selected_supervisor = st.selectbox("👨‍🏫 בחר מפקח/ת לקבלת פירוט מוסדי:", sups)
        df_sup = df_dist[df_dist['מפקח'] == selected_supervisor].copy()
        
        st.markdown(f"#### 📋 סטטוס ביצוע מוסדי משולב - מפקח: {selected_supervisor}")
        
        # בניית טבלת התצוגה הסופית
        df_display = pd.DataFrame()
        df_display['מוסד'] = df_sup['מוסד']
        df_display['רשות'] = df_sup['רשות']
        df_display['פוטנציאל מתמטיקה'] = df_sup['פוטנציאל מתמטיקה']
        df_display['ביצוע מתמטיקה'] = df_sup['אחוז מתמטיקה']
        df_display['פוטנציאל מדעים'] = df_sup['פוטנציאל מדעים']
        df_display['ביצוע מדעים'] = df_sup['אחוז מדעים']
        
        # מיון חכם: מוסדות עם הממוצע הנמוך ביותר (שזקוקים לעזרה בדחיפות) יופיעו ראשונים
        df_display['sort_score'] = df_display[['ביצוע מתמטיקה', 'ביצוע מדעים']].fillna(100.0).mean(axis=1)
        df_display = df_display.sort_values('sort_score').drop(columns=['sort_score'])
        
        # פונקציית סטיילינג מתקדמת לצביעת התאים בלבד
        def style_traffic_lights(data):
            style_df = pd.DataFrame('', index=data.index, columns=data.columns)
            
            for col, pot_col in [('ביצוע מתמטיקה', 'פוטנציאל מתמטיקה'), ('ביצוע מדעים', 'פוטנציאל מדעים')]:
                for idx in data.index:
                    val = data.loc[idx, col]
                    pot = data.loc[idx, pot_col]
                    
                    # מקרה שבו המוסד בכלל לא רלוונטי למקצוע (פוטנציאל 0 או NaN) - צביעה באפור נייטרלי
                    if pot == 0 or pd.isna(val):
                        style_df.loc[idx, col] = 'background-color: #f1f5f9; color: #94a3b8; text-align: center;'
                    elif val < 50.0:
                        style_df.loc[idx, col] = 'background-color: #ffe4e6; color: #9f1239; font-weight: 800; text-align: center;'
                    elif val <= 85.0:
                        style_df.loc[idx, col] = 'background-color: #fef3c7; color: #92400e; font-weight: 800; text-align: center;'
                    else:
                        style_df.loc[idx, col] = 'background-color: #d1fae5; color: #065f46; font-weight: 800; text-align: center;'
            return style_df

        # עיצוב והצגת פורמטים קריאים של אחוזים ומספרים
        format_dict = {
            'פוטנציאל מתמטיקה': lambda x: f"{int(x):,}" if x > 0 else "-",
            'פוטנציאל מדעים': lambda x: f"{int(x):,}" if x > 0 else "-",
            'ביצוע מתמטיקה': lambda x: f"{x:.1f}%" if pd.notna(x) else "-",
            'ביצוע מדעים': lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        }
        
        styled_table = df_display.style.apply(style_traffic_lights, axis=None).format(format_dict)
        
        # תצוגה נקייה ברוחב מקסימלי ללא אינדקסים מיותרים
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
        
        # מקרא סטאטוס מעוצב ברמת 2026
        st.markdown("""
        <div style="background-color: white; padding: 18px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); margin-top: 20px; border: 1px solid #e2e8f0;">
            <strong style="color:#0f172a; font-size: 1.05rem;">🎨 מקרא סטאטוס ביצוע (משבצות מקצועות בלבד):</strong><br><br>
            <span style="background-color: #ffe4e6; padding: 6px 14px; border-radius: 6px; color: #9f1239; font-weight: bold; margin-left: 15px;">🔴 0% - 50% (דורש התערבות דחופה)</span>
            <span style="background-color: #fef3c7; padding: 6px 14px; border-radius: 6px; color: #92400e; font-weight: bold; margin-left: 15px;">🟡 50% - 85% (במעקב פעיל)</span>
            <span style="background-color: #d1fae5; padding: 6px 14px; border-radius: 6px; color: #065f46; font-weight: bold; margin-left: 15px;">🟢 מעל 85% (מצב מצוין)</span>
            <span style="background-color: #f1f5f9; padding: 6px 14px; border-radius: 6px; color: #94a3b8; font-weight: bold;">⚪ המוסד אינו מוגדר למקצוע זה</span>
        </div>
        """, unsafe_allow_html=True)
