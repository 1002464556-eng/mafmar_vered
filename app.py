import streamlit as st
import pandas as pd
import numpy as np

# ==================== הגדרות עמוד ותצוגה ====================
st.set_page_config(page_title="תלמידים אשר ביצעו את משימת המפמ\"ר", layout="wide", page_icon="📊")

# עיצוב מותאם אישית לטובת יישור לימין (RTL) ומראה נקי
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    * { direction: rtl; text-align: right; }
    div[data-testid="metric-container"] {
        background-color: white;
        border-right: 5px solid #1D3557;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 1.1rem; font-weight: bold; color: #1d3557; margin-bottom: 5px; text-align: right; }
    .metric-value { font-size: 1.8rem; font-weight: bold; text-align: right; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
</style>
""", unsafe_allow_html=True)

st.title("תלמידים אשר ביצעו את משימת המפמ\"ר")
st.divider()

# ==================== פונקציות ניקוי ועיבוד נתונים ====================
def clean_percentage(val):
    """המרת ערכי אחוזים (טקסט, % או מספרים) למספר נקי בין 0 ל-100"""
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip()
    if 'Totals' in val_str or val_str == '':
        return 0.0
    has_percent = '%' in val_str
    val_str = val_str.replace('%', '')
    try:
        float_val = float(val_str)
        # אם זה שבר עשרוני קטן מ-1 ללא סימן אחוז, נהפוך אותו לאחוז (למשל 0.85 -> 85%)
        if float_val <= 1.0 and not has_percent and float_val > 0:
            return float_val * 100.0
        return float_val
    except:
        return 0.0

def clean_numeric(val):
    """ניקוי פסיקים מנתוני כמות תלמידים והפיכה למספר שלם"""
    if pd.isna(val):
        return 0
    val_str = str(val).replace(',', '').strip()
    try:
        return int(float(val_str))
    except:
        return 0

def process_sheet(df, subject_name):
    """עיבוד וניקוי הנתונים של לשונית/קובץ ספציפי"""
    # הסרת שורות סיכומים כלליים אם קיימות בקובץ
    df = df[~df['מוסד'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False)]
    df = df[df['מוסד'].notna() & (df['מוסד'] != '')]
    
    df['מקצוע'] = subject_name
    
    # ניקוי עמודת כמות תלמידים
    if 'פוטנציאל תלמידים' in df.columns:
        df['פוטנציאל תלמידים'] = df['פוטנציאל תלמידים'].apply(clean_numeric)
    else:
        df['פוטנציאל תלמידים'] = 0
        
    # ניקוי עמודת אחוז הביצוע שביקשת
    target_col = 'אחוז תלמידים שביצעו משימה אחת לפחות'
    if target_col in df.columns:
        df['אחוז ביצוע'] = df[target_col].apply(clean_percentage)
    else:
        # הגנה למקרה של שינוי קל בשם העמודה בקובץ
        alt_col = [c for c in df.columns if 'ביצעו משימה אחת' in c or 'אחוז תלמידים שביצעו' in c]
        if alt_col:
            df['אחוז ביצוע'] = df[alt_col[0]].apply(clean_percentage)
        else:
            df['אחוז ביצוע'] = 0.0
            
    return df

# ==================== טעינת קבצים מהממשק ====================
st.sidebar.header("📂 טעינת קובץ המפמ\"ר")
uploaded_file = st.sidebar.file_uploader("העלה את קובץ הנתונים (Excel או CSV):", type=["xlsx", "csv"])

df_all = pd.DataFrame()

if uploaded_file is not None:
    # טיפול בקובץ אקסל (תומך ב-2 לשוניות: מדעים ומתמטיקה)
    if uploaded_file.name.endswith('.xlsx'):
        excel_file = pd.ExcelFile(uploaded_file)
        sheets = excel_file.sheet_names
        
        df_list = []
        # חיפוש אוטומטי של הלשוניות לפי השם שלהן
        math_sheet = next((s for s in sheets if 'מתמטיקה' in s), None)
        sci_sheet = next((s for s in sheets if 'מדעים' in s), None)
        
        if math_sheet:
            df_math = pd.read_excel(uploaded_file, sheet_name=math_sheet, dtype=str)
            df_list.append(process_sheet(df_math, 'מתמטיקה'))
        if sci_sheet:
            df_sci = pd.read_excel(uploaded_file, sheet_name=sci_sheet, dtype=str)
            df_list.append(process_sheet(df_sci, 'מדעים'))
            
        # אם הלשוניות לא נקראו בדיוק בשמות האלו, נאפשר למשתמש לבחור אותן ידנית
        if not df_list:
            st.warning("⚠️ לא נמצאו לשוניות מדויקות בשם 'מתמטיקה' או 'מדעים'. אנא שייך את הלשוניות:")
            selected_math = st.selectbox("בחר לשונית עבור מתמטיקה:", ["ללא"] + sheets)
            selected_sci = st.selectbox("בחר לשונית עבור מדעים:", ["ללא"] + sheets)
            
            if selected_math != "ללא":
                df_math = pd.read_excel(uploaded_file, sheet_name=selected_math, dtype=str)
                df_list.append(process_sheet(df_math, 'מתמטיקה'))
            if selected_sci != "ללא":
                df_sci = pd.read_excel(uploaded_file, sheet_name=selected_sci, dtype=str)
                df_list.append(process_sheet(df_sci, 'מדעים'))
        
        if df_list:
            df_all = pd.concat(df_list, ignore_index=True)
            
    # טיפול בקובץ CSV בודד (למשל הקובץ שהעלית npnr)
    elif uploaded_file.name.endswith('.csv'):
        subject = st.sidebar.radio("לאיזה מקצוע שייך קובץ ה-CSV שהעלית?", ["מתמטיקה", "מדעים"])
        try:
            df_csv = pd.read_csv(uploaded_file, encoding='utf-8-sig', dtype=str)
        except:
            df_csv = pd.read_csv(uploaded_file, encoding='cp1255', dtype=str)
            
        df_all = process_sheet(df_csv, subject)

# אם לא הועלה קובץ, נציג הודעה ידידותית למשתמש
if df_all.empty:
    st.info("💡 אנא העלה את קובץ המפמ\"ר שלך בסרגל הצד כדי להציג את הנתונים.")
    st.stop()

# ==================== חלק א': פילוח מחוזי ומדדים ====================
if 'מחוז' in df_all.columns:
    districts = sorted(df_all['מחוז'].dropna().unique())
    selected_district = st.selectbox("🎯 שלב 1: בחר מחוז לצפייה:", districts)
    
    df_dist = df_all[df_all['מחוז'] == selected_district]
    
    st.markdown(f"### נתונים כלליים עבור מחוז: **{selected_district}**")
    col1, col2 = st.columns(2)
    
    # חישוב נתונים למתמטיקה
    with col1:
        df_math_dist = df_dist[df_dist['מקצוע'] == 'מתמטיקה']
        total_students_math = df_math_dist['פוטנציאל תלמידים'].sum()
        if total_students_math > 0:
            avg_pct_math = (df_math_dist['אחוז ביצוע'] * df_math_dist['פוטנציאל תלמידים']).sum() / total_students_math
        else:
            avg_pct_math = df_math_dist['אחוז ביצוע'].mean() if not df_math_dist.empty else 0.0
            
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #E63946; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div class="metric-title">📐 מקצוע: מתמטיקה</div>
            <div class="metric-value">{avg_pct_math:.1f}% ביצוע מחוזי</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">כמות תלמידים כוללת: {total_students_math:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # חישוב נתונים למדעים
    with col2:
        df_sci_dist = df_dist[df_dist['מקצוע'] == 'מדעים']
        total_students_sci = df_sci_dist['פוטנציאל תלמידים'].sum()
        if total_students_sci > 0:
            avg_pct_sci = (df_sci_dist['אחוז ביצוע'] * df_sci_dist['פוטנציאל תלמידים']).sum() / total_students_sci
        else:
            avg_pct_sci = df_sci_dist['אחוז ביצוע'].mean() if not df_sci_dist.empty else 0.0
            
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #1D3557; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div class="metric-title">🔬 מקצוע: מדעים</div>
            <div class="metric-value">{avg_pct_sci:.1f}% ביצוע מחוזי</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">כמות תלמידים כוללת: {total_students_sci:,}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # ==================== חלק ב': בחירת מפקח וצביעת מוסדות ====================
    if 'מפקח' in df_dist.columns:
        sups = sorted(df_dist['מפקח'].dropna().unique())
        selected_supervisor = st.selectbox("👨‍🏫 שלב 2: בחר שם מפקח לקבלת מידע על מוסדותיו:", sups)
        
        if selected_supervisor:
            df_sup = df_dist[df_dist['מפקח'] == selected_supervisor]
            st.subheader(f"📋 רשימת מוסדות תחת פיקוחו/ה של: {selected_supervisor}")
            
            # פונקציית עיצוב וצביעה לפי התנאים שביקשת
            def color_picker(row):
                val = row['אחוז ביצוע']
                if val < 50.0:
                    color = '#ffccd5'  # אדום בהיר (0-50%)
                elif val <= 85.0:
                    color = '#fef3c7'  # צהוב בהיר (50-85%)
                else:
                    color = '#d1fae5'  # ירוק בהיר (מעל 85%)
                return [f'background-color: {color}; color: black;' for _ in row]
            
            # עמודות להצגה בטבלה
            cols_to_show = ['מוסד', 'רשות', 'כיתה', 'מקבילה', 'פוטנציאל תלמידים', 'אחוז תלמידים שביצעו משימה אחת לפחות']
            available_cols = [c for c in cols_to_show if c in df_sup.columns] + ['אחוז ביצוע']
            
            tab1, tab2 = st.tabs(["📐 מתמטיקה", "🔬 מדעים"])
            
            with tab1:
                df_sup_math = df_sup[df_sup['מקצוע'] == 'מתמטיקה']
                if not df_sup_math.empty:
                    df_disp_math = df_sup_math[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                    # שינוי פורמט התצוגה של אחוז הביצוע שיראה יפה
                    styled_math = df_disp_math.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                    st.dataframe(styled_math, use_container_width=True, hide_index=True)
                else:
                    st.info(f"לא נמצאו נתונים במתמטיקה עבור המפקח {selected_supervisor} במחוז זה.")
                    
            with tab2:
                df_sup_sci = df_sup[df_sup['מקצוע'] == 'מדעים']
                if not df_sup_sci.empty:
                    df_disp_sci = df_sup_sci[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                    styled_sci = df_disp_sci.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                    st.dataframe(styled_sci, use_container_width=True, hide_index=True)
                else:
                    st.info(f"לא נמצאו נתונים במדעים עבור המפקח {selected_supervisor} במחוז זה.")
                    
            # מקרא צבעים בתחתית
            st.markdown("""
            <br>
            <div style="background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: inline-block;">
                <strong>🎨 מקרא צבעים (אחוז תלמידים שביצעו משימה אחת לפחות):</strong> &nbsp;
                <span style="background-color: #ffccd5; padding: 3px 8px; border-radius: 3px; color: black;">🔴 0% - 50%</span> &nbsp;
                <span style="background-color: #fef3c7; padding: 3px 8px; border-radius: 3px; color: black;">🟡 50% - 85%</span> &nbsp;
                <span style="background-color: #d1fae5; padding: 3px 8px; border-radius: 3px; color: black;">🟢 85% ומעלה</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("לא נמצאה עמודת 'מפקח' בקובץ שהועלה.")
else:
    st.warning("לא נמצאה עמודת 'מחוז' בקובץ שהועלה.")
