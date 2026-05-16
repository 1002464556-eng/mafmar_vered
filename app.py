import streamlit as st
import pandas as pd
import numpy as np
import os

# ==================== הגדרות עמוד ותצוגה ====================
st.set_page_config(page_title="תלמידים אשר ביצעו את משימת המפמ\"ר", layout="wide", page_icon="📊")

# עיצוב מותאם אישית ליישור לימין (RTL) ומראה נקי ומקצועי
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
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
</style>
""", unsafe_allow_html=True)

st.title("📊 תלמידים אשר ביצעו את משימת המפמ\"ר")
st.divider()

# ==================== פונקציות ניקוי ועיבוד נתונים ====================
def clean_percentage(val):
    """המרת ערכי אחוזים מטקסט או מספר לשבר עשרוני של אחוז (0-100)"""
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip()
    if 'Totals' in val_str or val_str == '':
        return 0.0
    has_percent = '%' in val_str
    val_str = val_str.replace('%', '').replace(',', '')
    try:
        float_val = float(val_str)
        # אם זה שבר עשרוני קטן מ-1 (למשל 0.85) ללא סימן %, נהפוך אותו ל-85%
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
    """עיבוד וניקוי הנתונים של לשונית ספציפית באקסל"""
    # ניקוי רווחים משמות העמודות
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'מוסד' in df.columns:
        # הסרת שורות סיכומים כלליים של המערכת (כמו שורת הטוטאלס שקיימת בקובץ)
        df = df[~df['מוסד'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False)]
        df = df[df['מוסד'].notna() & (df['מוסד'].astype(str).str.strip() != '')]
    else:
        return pd.DataFrame()
    
    df['מקצוע'] = subject_name
    
    # ניקוי עמודת כמות תלמידים
    if 'פוטנציאל תלמידים' in df.columns:
        df['פוטנציאל תלמידים'] = df['פוטנציאל תלמידים'].apply(clean_numeric)
    else:
        df['פוטנציאל תלמידים'] = 0
        
    # ניקוי עמודת אחוז הביצוע המדויקת מהקובץ שלך
    target_col = 'אחוז תלמידים שביצעו משימה אחת לפחות'
    if target_col in df.columns:
        df['אחוז ביצוע'] = df[target_col].apply(clean_percentage)
    else:
        alt_col = [c for c in df.columns if 'ביצעו משימה אחת' in c or 'אחוז תלמידים' in c]
        if alt_col:
            df['אחוז ביצוע'] = df[alt_col[0]].apply(clean_percentage)
        else:
            df['אחוז ביצוע'] = 0.0
            
    return df

@st.cache_data(ttl=600)
def load_packaged_data():
    """סריקה אוטומטית של התיקייה וטעינת קובץ האקסל שהועלה ל-GitHub"""
    # חיפוש קובץ אקסל בתקייה הנוכחית
    excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx') or f.endswith('.xls')]
    if not excel_files:
        return pd.DataFrame(), "לא पाया קובץ אקסל (.xlsx) בתיקיית ה-GitHub. אנא ודא שהעלית את הקובץ לתוך המאגר."
    
    file_path = excel_files[0] # לוקח את קובץ האקסל הראשון
    
    try:
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names
        
        df_list = []
        math_sheet = next((s for s in sheets if 'מתמטיקה' in s), None)
        sci_sheet = next((s for s in sheets if 'מדעים' in s), None)
        
        if math_sheet:
            df_math = pd.read_excel(file_path, sheet_name=math_sheet, dtype=str)
            processed_math = process_sheet(df_math, 'מתמטיקה')
            if not processed_math.empty:
                df_list.append(processed_math)
        if sci_sheet:
            df_sci = pd.read_excel(file_path, sheet_name=sci_sheet, dtype=str)
            processed_sci = process_sheet(df_sci, 'מדעים')
            if not processed_sci.empty:
                df_list.append(processed_sci)
            
        # גיבוי: אם הלשוניות לא נקראו בדיוק ככה, ניקח את 2 הלשוניות הראשונות בקובץ
        if not df_list and len(sheets) >= 2:
            df_list.append(process_sheet(pd.read_excel(file_path, sheet_name=sheets[0], dtype=str), 'מתמטיקה'))
            df_list.append(process_sheet(pd.read_excel(file_path, sheet_name=sheets[1], dtype=str), 'מדעים'))
            
        if not df_list:
            return pd.DataFrame(), "קובץ האקסל נמצא אך הלשוניות בתוכו ריקות או לא תואמות למבנה הנתונים."
            
        return pd.concat(df_list, ignore_index=True), None
    except Exception as e:
        return pd.DataFrame(), f"שגיאה בטעינת קובץ האקסל מה-GitHub: {str(e)}"

# ==================== טעינת הנתונים מהאריזה ====================
df_all, error_msg = load_packaged_data()

if error_msg:
    st.error(f"❌ {error_msg}")
    st.info("💡 הנחיה: ודא שהעלית את קובץ האקסל הסופי שלך (בפורמט .xlsx עם 2 לשוניות) ישירות לתוך ה-Repository ב-GitHub.")
    st.stop()

# ==================== חלק א': פילוח מחוזי ומדדים ====================
if 'מחוז' in df_all.columns:
    districts = sorted(df_all['מחוז'].dropna().unique())
    selected_district = st.selectbox("🎯 בחר מחוז לצפייה:", districts)
    
    df_dist = df_all[df_all['מחוז'] == selected_district]
    
    st.markdown(f"### נתונים כלליים ומדדים עבור מחוז: **{selected_district}**")
    col1, col2 = st.columns(2)
    
    # חישוב נתונים למתמטיקה במחוז (ממוצע משוקלל אמיתי)
    with col1:
        df_math_dist = df_dist[df_dist['מקצוע'] == 'מתמטיקה']
        total_students_math = df_math_dist['פוטנציאל תלמידים'].sum()
        if total_students_math > 0:
            avg_pct_math = (df_math_dist['אחוז ביצוע'] * df_math_dist['פוטנציאל תלמידים']).sum() / total_students_math
        else:
            avg_pct_math = df_math_dist['אחוז ביצוע'].mean() if not df_math_dist.empty else 0.0
            
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #E63946; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); direction: rtl; text-align: right;">
            <div style="font-size: 1.1rem; font-weight: bold; color: #E63946; margin-bottom: 5px; direction: rtl; text-align: right;">📐 מקצוע: מתמטיקה</div>
            <div style="font-size: 1.8rem; font-weight: bold; direction: rtl; text-align: right; color: #1e293b;">{avg_pct_math:.1f}% ביצוע מחוזי</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px; direction: rtl; text-align: right;">פוטנציאל תלמידים כולל: {total_students_math:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # חישוב נתונים למדעים במחוז (ממוצע משוקלל אמיתי)
    with col2:
        df_sci_dist = df_dist[df_dist['מקצוע'] == 'מדעים']
        total_students_sci = df_sci_dist['פוטנציאל תלמידים'].sum()
        if total_students_sci > 0:
            avg_pct_sci = (df_sci_dist['אחוז ביצוע'] * df_sci_dist['פוטנציאל תלמידים']).sum() / total_students_sci
        else:
            avg_pct_sci = df_sci_dist['אחוז ביצוע'].mean() if not df_sci_dist.empty else 0.0
            
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #1D3557; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); direction: rtl; text-align: right;">
            <div style="font-size: 1.1rem; font-weight: bold; color: #1D3557; margin-bottom: 5px; direction: rtl; text-align: right;">🔬 מקצוע: מדעים</div>
            <div style="font-size: 1.8rem; font-weight: bold; direction: rtl; text-align: right; color: #1e293b;">{avg_pct_sci:.1f}% ביצוע מחוזי</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px; direction: rtl; text-align: right;">פוטנציאל תלמידים כולל: {total_students_sci:,}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # ==================== חלק ב': בחירת מפקח וצביעת מוסדות ====================
    if 'מפקח' in df_dist.columns:
        sups = sorted(df_dist['מפקח'].dropna().unique())
        selected_supervisor = st.selectbox("👨‍🏫 בחר שם מפקח לקבלת מידע על מוסדותיו:", sups)
        
        if selected_supervisor:
            df_sup = df_dist[df_dist['מפקח'] == selected_supervisor]
            st.subheader(f"📋 רשימת מוסדות תחת פיקוחו/ה של: {selected_supervisor}")
            
            # פונקציית צביעה מותנית לפי חוקי הצבע שביקשת
            def color_picker(row):
                val = row['אחוז ביצוע']
                if val < 50.0:
                    color = '#ffccd5'  # אדום בהיר (0-50%)
                elif val <= 85.0:
                    color = '#fef3c7'  # צהוב בהיר (50-85%)
                else:
                    color = '#d1fae5'  # ירוק בהיר (מעל 85%)
                return [f'background-color: {color}; color: black; font-weight: 500;' for _ in row]
            
            # עמודות להצגה בטבלה
            cols_to_show = ['מוסד', 'רשות', 'כיתה', 'מקבילה', 'פוטנציאל תלמידים', 'אחוז תלמידים שביצעו משימה אחת לפחות']
            available_cols = [c for c in cols_to_show if c in df_sup.columns] + ['אחוז ביצוע']
            
            tab1, tab2 = st.tabs(["📐 מתמטיקה", "🔬 מדעים"])
            
            with tab1:
                df_sup_math = df_sup[df_sup['מקצוע'] == 'מתמטיקה']
                if not df_sup_math.empty:
                    # מיון מהנמוך לגבוה - מוסדות באדום/סיכון קופצים ישר למעלה לטיפול המפקח!
                    df_disp_math = df_sup_math[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                    styled_math = df_disp_math.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                    st.dataframe(styled_math, use_container_width=True, hide_index=True)
                else:
                    st.info(f"לא נמצאו נתונים במתמטיקה עבור המפקח {selected_supervisor}.")
                    
            with tab2:
                df_sup_sci = df_sup[df_sup['מקצוע'] == 'מדעים']
                if not df_sup_sci.empty:
                    df_disp_sci = df_sup_sci[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                    styled_sci = df_disp_sci.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                    st.dataframe(styled_sci, use_container_width=True, hide_index=True)
                else:
                    st.info(f"לא נמצאו נתונים במדעים עבור המפקח {selected_supervisor}.")
                    
            # מקרא צבעים בתחתית הדף
            st.markdown("""
            <br>
            <div style="background-color: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: inline-block; direction: rtl; text-align: right;">
                <strong style="color:#1d3557;">🎨 מקרא צבעים סטאטוס ביצוע ("אחוז תלמידים שביצעו משימה אחת לפחות"):</strong> &nbsp;&nbsp;
                <span style="background-color: #ffccd5; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🔴 0% - 50% (בסיכון גבוה)</span> &nbsp;&nbsp;
                <span style="background-color: #fef3c7; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🟡 50% - 85% (בטיפול)</span> &nbsp;&nbsp;
                <span style="background-color: #d1fae5; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🟢 85% ומעלה (מצוין)</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("לא נמצאה עמודת 'מפקח' בקובץ המקור.")
else:
    st.warning("לא נמצאה עמודת 'מחוז' בקובץ המקור.")
