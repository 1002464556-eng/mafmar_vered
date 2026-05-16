import streamlit as st
import pandas as pd
import numpy as np
import os

# ==================== הגדרות תצוגה עתידניות (2026 Design) ====================
st.set_page_config(page_title="דשבורד מפמ\"ר לאומי", layout="wide", page_icon="🌐")

st.markdown("""
<style>
    /* הגדרות רקע ופונטים */
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');
    
    .stApp {
        background-color: #f4f7f6;
        font-family: 'Heebo', sans-serif;
    }
    * { direction: rtl; text-align: right; }
    
    /* כותרת הדשבורד */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        margin-bottom: 30px;
    }
    .main-header h1 { color: white !important; font-weight: 800; font-size: 2.5rem; margin: 0; text-align: center; }
    .main-header p { font-size: 1.2rem; opacity: 0.9; margin-top: 5px; text-align: center; }
    
    /* כרטיסיות המדדים (Metric Cards) */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-right: 6px solid #e2e8f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .metric-math { border-right-color: #ec4899; } /* ורוד-אדום חדיש למתמטיקה */
    .metric-sci { border-right-color: #3b82f6; } /* כחול הייטק למדעים */
    
    .metric-title { font-size: 1.1rem; color: #64748b; font-weight: 600; margin-bottom: 8px; }
    .metric-value { font-size: 2.2rem; color: #0f172a; font-weight: 800; line-height: 1; }
    .metric-sub { font-size: 0.9rem; color: #94a3b8; margin-top: 8px; font-weight: 400; }
    
    /* טבלאות נקיות שלא חותכות טקסט */
    .stDataFrame div table {
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important;
    }
    .stDataFrame td, .stDataFrame th {
        white-space: normal !important;
        word-break: keep-all !important;
        font-size: 14px;
        padding: 12px 8px !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🌐 מערכת ניטור לאומית - משימות מפמ"ר</h1>
    <p>תמונת מצב עדכנית למחוזות ומפקחים | עיבוד נתונים חכם</p>
</div>
""", unsafe_allow_html=True)

# ==================== מנוע עיבוד נתונים (Data Engine) ====================
def clean_numeric(val):
    if pd.isna(val): return 0
    val_str = str(val).replace(',', '').replace('%', '').strip()
    try: return int(float(val_str))
    except: return 0

def process_subject_file(file_path, subject_name):
    """קריאת קובץ יחיד, ניקוי, ושקלול ברמת מוסד"""
    try:
        if file_path.endswith('.csv'):
            try: df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            except: df = pd.read_csv(file_path, encoding='cp1255', dtype=str)
        else:
            df = pd.read_excel(file_path, dtype=str)
    except:
        return pd.DataFrame()
        
    df.columns = [str(c).strip() for c in df.columns]
    
    # סינון שורות סיכום כלליות של המערכת
    if 'מוסד' in df.columns:
        df = df[~df['מוסד'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False)]
        df = df[df['מוסד'].notna() & (df['מוסד'].astype(str).str.strip() != '')]
    else:
        return pd.DataFrame()

    # חילוץ נתוני הפוטנציאל והביצוע בפועל
    df['פוטנציאל'] = df['פוטנציאל תלמידים'].apply(clean_numeric) if 'פוטנציאל תלמידים' in df.columns else 0
    
    completed_col = next((c for c in df.columns if 'תלמידים שביצעו' in c and 'אחוז' not in c), None)
    if not completed_col:
        # במקרה שאין עמודת כמות אלא רק אחוז, נחשב חזרה את הכמות
        pct_col = next((c for c in df.columns if 'אחוז' in c and 'ביצעו' in c), None)
        if pct_col:
            df['אחוז_נקי'] = df[pct_col].apply(lambda x: float(str(x).replace('%','')) if pd.notna(x) and str(x).strip() else 0.0)
            # תיקון אחוזים שכתובים כשבר עשרוני (0.85 במקום 85)
            df['אחוז_נקי'] = np.where(df['אחוז_נקי'] <= 1.0, df['אחוז_נקי'] * 100, df['אחוז_נקי'])
            df['ביצעו'] = (df['אחוז_נקי'] / 100.0) * df['פוטנציאל']
        else:
            df['ביצעו'] = 0
    else:
        df['ביצעו'] = df[completed_col].apply(clean_numeric)

    # שקלול כל השורות (כיתות) לאותו מוסד לשורה אחת!
    grouped = df.groupby('מוסד').agg({
        'מחוז': 'first',
        'מפקח': 'first',
        'רשות': 'first',
        'פוטנציאל': 'sum',
        'ביצעו': 'sum'
    }).reset_index()
    
    # חישוב אחוז ביצוע מדויק למוסד
    grouped[f'אחוז {subject_name}'] = np.where(
        grouped['פוטנציאל'] > 0, 
        (grouped['ביצעו'] / grouped['פוטנציאל']) * 100.0, 
        0.0
    )
    
    # שינוי שמות עמודות להכנה למיזוג
    grouped.rename(columns={
        'פוטנציאל': f'פוטנציאל {subject_name}',
        'ביצעו': f'ביצעו {subject_name}'
    }, inplace=True)
    
    return grouped

@st.cache_data(ttl=600)
def load_and_merge_data():
    """חיפוש 2 הקבצים בתיקייה ומיזוגם לטבלת-על אחת"""
    files = os.listdir('.')
    
    # זיהוי אוטומטי של קובץ מתמטיקה וקובץ מדעים (Excel או CSV)
    math_file = next((f for f in files if 'מתמטיק' in f and (f.endswith('.csv') or f.endswith('.xlsx'))), None)
    sci_file = next((f for f in files if 'מדע' in f and (f.endswith('.csv') or f.endswith('.xlsx'))), None)
    
    df_math = process_subject_file(math_file, 'מתמטיקה') if math_file else pd.DataFrame()
    df_sci = process_subject_file(sci_file, 'מדעים') if sci_file else pd.DataFrame()
    
    if df_math.empty and df_sci.empty:
        return pd.DataFrame(), "לא נמצאו קבצי נתונים (מתמטיקה / מדעים) בתיקייה."

    # מיזוג חכם של שני הקבצים
    if not df_math.empty and not df_sci.empty:
        df_merged = pd.merge(df_math, df_sci[['מוסד', 'פוטנציאל מדעים', 'ביצוע מדעים', 'אחוז מדעים']], 
                             on='מוסד', how='outer')
    elif not df_math.empty:
        df_merged = df_math.copy()
        for c in ['פוטנציאל מדעים', 'ביצוע מדעים', 'אחוז מדעים']: df_merged[c] = np.nan
    else:
        df_merged = df_sci.copy()
        for c in ['פוטנציאל מתמטיקה', 'ביצוע מתמטיקה', 'אחוז מתמטיקה']: df_merged[c] = np.nan

    # השלמת נתוני מחוז/מפקח שחסרים בגלל ה-Outer Merge
    df_merged['מחוז'] = df_merged['מחוז'].fillna('לא ידוע')
    df_merged['מפקח'] = df_merged['מפקח'].fillna('לא ידוע')
    df_merged['רשות'] = df_merged['רשות'].fillna('-')
    
    return df_merged, None

# ==================== הפעלת המערכת ====================
df_main, error_msg = load_and_merge_data()

if error_msg:
    st.error(f"⚠️ {error_msg}")
    st.info("💡 אנא ודא שהעלית ל-GitHub את שני הקבצים, ושמם מכיל את המילים 'מתמטיקה' ו-'מדעים'.")
    st.stop()

# ==================== שלב 1: פילוח מחוזי מקיף ====================
districts = sorted([d for d in df_main['מחוז'].unique() if d != 'לא ידוע'])
if not districts:
    st.error("לא זוהו מחוזות תקינים בקבצים.")
    st.stop()

selected_district = st.selectbox("🎯 בחר מחוז להצגת הנתונים:", districts)
df_dist = df_main[df_main['מחוז'] == selected_district]

# חישוב שקלול מחוזי אמיתי (סך כל התלמידים שביצעו לחלק לסך הפוטנציאל במחוז)
dist_pot_math = df_dist['פוטנציאל מתמטיקה'].sum()
dist_done_math = df_dist['ביצוע מתמטיקה'].sum()
dist_avg_math = (dist_done_math / dist_pot_math * 100) if dist_pot_math > 0 else 0.0

dist_pot_sci = df_dist['פוטנציאל מדעים'].sum()
dist_done_sci = df_dist['ביצוע מדעים'].sum()
dist_avg_sci = (dist_done_sci / dist_pot_sci * 100) if dist_pot_sci > 0 else 0.0

st.markdown(f"<h3 style='color:#1e3c72; margin-top:10px;'>מבט-על: מחוז {selected_district}</h3>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="metric-card metric-math">
        <div class="metric-title">📐 הישגי מחוז - מתמטיקה</div>
        <div class="metric-value">{dist_avg_math:.1f}%</div>
        <div class="metric-sub">פוטנציאל תלמידים כולל: <b>{int(dist_pot_math):,}</b></div>
    </div>
    """, unsafe_allow_html=True)
    
with col2:
    st.markdown(f"""
    <div class="metric-card metric-sci">
        <div class="metric-title">🔬 הישגי מחוז - מדעים</div>
        <div class="metric-value">{dist_avg_sci:.1f}%</div>
        <div class="metric-sub">פוטנציאל תלמידים כולל: <b>{int(dist_pot_sci):,}</b></div>
    </div>
    """, unsafe_allow_html=True)

st.write("<br>", unsafe_allow_html=True)

# ==================== שלב 2: ניתוח ברמת מפקח (רמזור חכם) ====================
sups = sorted([s for s in df_dist['מפקח'].unique() if s != 'לא ידוע'])
if sups:
    selected_supervisor = st.selectbox("👨‍🏫 בחר מפקח/ת לניתוח מוסדות:", sups)
    df_sup = df_dist[df_dist['מפקח'] == selected_supervisor].copy()
    
    st.markdown(f"#### 📋 סטטוס ביצוע מוסדות תחת פיקוח: **{selected_supervisor}**")
    
    # הכנת הנתונים לתצוגה סופית ויפה
    df_display = pd.DataFrame()
    df_display['מוסד'] = df_sup['מוסד']
    df_display['רשות'] = df_sup['רשות']
    df_display['פוטנציאל מתמטיקה'] = df_sup['פוטנציאל מתמטיקה'].fillna(0).astype(int)
    df_display['ביצוע מתמטיקה'] = df_sup['אחוז מתמטיקה']
    df_display['פוטנציאל מדעים'] = df_sup['פוטנציאל מדעים'].fillna(0).astype(int)
    df_display['ביצוע מדעים'] = df_sup['אחוז מדעים']
    
    # מיון לפי בתי הספר שזקוקים לעזרה הכי דחופה (הממוצע הנמוך משני המקצועות)
    df_display['ממוצע_כללי'] = df_display[['ביצוע מתמטיקה', 'ביצוע מדעים']].mean(axis=1)
    df_display = df_display.sort_values('ממוצע_כללי').drop(columns=['ממוצע_כללי'])
    
    # פונקציית צביעה (רמזור) רק למשבצות הביצוע
    def traffic_light_cells(data):
        style_df = pd.DataFrame('', index=data.index, columns=data.columns)
        
        for col, pot_col in [('ביצוע מתמטיקה', 'פוטנציאל מתמטיקה'), ('ביצוע מדעים', 'פוטנציאל מדעים')]:
            for idx in data.index:
                val = data.loc[idx, col]
                pot = data.loc[idx, pot_col]
                
                # אם למוסד אין תלמידים במקצוע זה (הוא לא קיים בקובץ הספציפי) נצבע באפור ניטרלי
                if pot == 0 or pd.isna(val):
                    style_df.loc[idx, col] = 'background-color: #f1f5f9; color: #94a3b8; text-align: center;'
                elif val < 50.0:
                    style_df.loc[idx, col] = 'background-color: #ffe4e6; color: #9f1239; font-weight: 800; text-align: center;'
                elif val <= 85.0:
                    style_df.loc[idx, col] = 'background-color: #fef3c7; color: #92400e; font-weight: 800; text-align: center;'
                else:
                    style_df.loc[idx, col] = 'background-color: #d1fae5; color: #065f46; font-weight: 800; text-align: center;'
        return style_df

    # עיצוב מיוחד להצגת אפס או חוסר נתונים כ-"-" במקום 0.0%
    format_dict = {
        'פוטנציאל מתמטיקה': lambda x: f"{x:,}" if x > 0 else "-",
        'פוטנציאל מדעים': lambda x: f"{x:,}" if x > 0 else "-",
        'ביצוע מתמטיקה': lambda x: f"{x:.1f}%" if pd.notna(x) and x >= 0 else "-",
        'ביצוע מדעים': lambda x: f"{x:.1f}%" if pd.notna(x) and x >= 0 else "-"
    }
    
    styled_table = df_display.style.apply(traffic_light_cells, axis=None).format(format_dict)
    
    # תצוגת הטבלה
    st.dataframe(styled_table, use_container_width=True, hide_index=True)

    # מקרא צבעים חדיש
    st.markdown("""
    <div style="background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 15px; border: 1px solid #e2e8f0;">
        <strong style="color:#0f172a; font-size: 1.05rem;">🎨 מקרא סטאטוס ביצוע (משבצות מקצועות בלבד):</strong><br><br>
        <span style="background-color: #ffe4e6; padding: 6px 12px; border-radius: 6px; color: #9f1239; font-weight: bold; margin-left: 15px;">🔴 0% - 50% (דורש התערבות)</span>
        <span style="background-color: #fef3c7; padding: 6px 12px; border-radius: 6px; color: #92400e; font-weight: bold; margin-left: 15px;">🟡 50% - 85% (במעקב)</span>
        <span style="background-color: #d1fae5; padding: 6px 12px; border-radius: 6px; color: #065f46; font-weight: bold; margin-left: 15px;">🟢 מעל 85% (מצוין)</span>
        <span style="background-color: #f1f5f9; padding: 6px 12px; border-radius: 6px; color: #94a3b8; font-weight: bold;">⚪ אין פוטנציאל למקצוע זה</span>
    </div>
    """, unsafe_allow_html=True)
