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
    """עיבוד וניקוי הנתונים של קובץ או לשונית באקסל"""
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'מוסד' in df.columns:
        df = df[~df['מוסד'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False)]
        df = df[df['מוסד'].notna() & (df['מוסד'].astype(str).str.strip() != '')]
    else:
        return pd.DataFrame()
    
    df['מקצוע'] = subject_name
    
    if 'פוטנציאל תלמידים' in df.columns:
        df['פוטנציאל תלמידים'] = df['פוטנציאל תלמידים'].apply(clean_numeric)
    else:
        df['פוטנציאל תלמידים'] = 0
        
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
    """סריקה אוטומטית ותמיכה מלאה הן בקבצי אקסל (.xlsx) והן בקבצי (.csv)"""
    files = os.listdir('.')
    excel_files = [f for f in files if f.endswith('.xlsx') or f.endswith('.xls')]
    csv_files = [f for f in files if f.endswith('.csv')]
    
    df_list = []
    
    if excel_files:
        for file_path in excel_files:
            try:
                excel_file = pd.ExcelFile(file_path)
                for sheet in excel_file.sheet_names:
                    df_sheet = pd.read_excel(file_path, sheet_name=sheet, dtype=str)
                    subj = 'מתמטיקה' if 'מתמטיקה' in sheet else ('מדעים' if 'מדעים' in sheet else 'כללי')
                    processed = process_sheet(df_sheet, subj)
                    if not processed.empty:
                        df_list.append(processed)
            except:
                continue
                
    if not df_list and csv_files:
        for file_path in csv_files:
            df_csv = None
            for encoding in ['utf-8-sig', 'cp1255', 'utf-8', 'latin1']:
                try:
                    df_csv = pd.read_csv(file_path, encoding=encoding, dtype=str)
                    break
                except:
                    continue
            
            if df_csv is not None:
                subj = 'מתמטיקה' if 'מתמטיקה' in file_path else ('מדעים' if 'מדעים' in file_path else 'כללי')
                processed = process_sheet(df_csv, subj)
                if not processed.empty:
                    df_list.append(processed)
                    
    if not df_list:
        return pd.DataFrame(), "לא נמצא קובץ נתונים תואם (CSV או Excel) בתיקיית ה-GitHub. אנא ודא שהקובץ הועלה למאגר כהלכה."
        
    return pd.concat(df_list, ignore_index=True), None

# ==================== טעינת הנתונים ====================
df_all, error_msg = load_packaged_data()

if error_msg:
    st.error(f"❌ {error_msg}")
    st.stop()

# ==================== חלק א': פילוח מחוזי ומדדים ====================
if 'מחוז' in df_all.columns:
    districts = sorted(df_all['מחוז'].dropna().unique())
    selected_district = st.selectbox("🎯 בחר מחוז לצפייה:", districts)
    
    df_dist = df_all[df_all['מחוז'] == selected_district]
    st.markdown(f"### נתונים כלליים ומדדים עבור מחוז: **{selected_district}**")
    
    subjects_in_data = df_dist['מקצוע'].unique()
    
    if len(subjects_in_data) == 1 and subjects_in_data[0] == 'כללי':
        total_students = df_dist['פוטנציאל תלמידים'].sum()
        if total_students > 0:
            avg_pct = (df_dist['אחוז ביצוע'] * df_dist['פוטנציאל תלמידים']).sum() / total_students
        else:
            avg_pct = df_dist['אחוז ביצוע'].mean() if not df_dist.empty else 0.0
            
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #1D3557; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); direction: rtl; text-align: right;">
            <div style="font-size: 1.1rem; font-weight: bold; color: #1D3557; margin-bottom: 5px;">📊 משימת המפמ"ר - נתוני ביצוע</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #1e293b;">{avg_pct:.1f}% ביצוע מחוזי משוקלל</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">פוטנציאל תלמידים כולל במחוז: {total_students:,}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2 = st.columns(2)
        with col1:
            df_math_dist = df_dist[df_dist['מקצוע'] == 'מתמטיקה']
            if df_math_dist.empty: df_math_dist = df_dist 
            total_students_math = df_math_dist['פוטנציאל תלמידים'].sum()
            if total_students_math > 0:
                avg_pct_math = (df_math_dist['אחוז ביצוע'] * df_math_dist['פוטנציאל תלמידים']).sum() / total_students_math
            else:
                avg_pct_math = df_math_dist['אחוז ביצוע'].mean() if not df_math_dist.empty else 0.0
                
            st.markdown(f"""
            <div style="background-color: white; border-right: 5px solid #E63946; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="font-size: 1.1rem; font-weight: bold; color: #E63946; margin-bottom: 5px;">📐 מקצוע: מתמטיקה</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #1e293b;">{avg_pct_math:.1f}% ביצוע מחוזי</div>
                <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">פוטנציאל תלמידים כולל: {total_students_math:,}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            df_sci_dist = df_dist[df_dist['מקצוע'] == 'מדעים']
            if df_sci_dist.empty: df_sci_dist = df_dist 
            total_students_sci = df_sci_dist['פוטנציאל תלמידים'].sum()
            if total_students_sci > 0:
                avg_pct_sci = (df_sci_dist['אחוז ביצוע'] * df_sci_dist['פוטנציאל תלמידים']).sum() / total_students_sci
            else:
                avg_pct_sci = df_sci_dist['אחוז ביצוע'].mean() if not df_sci_dist.empty else 0.0
                
            st.markdown(f"""
            <div style="background-color: white; border-right: 5px solid #1D3557; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="font-size: 1.1rem; font-weight: bold; color: #1D3557; margin-bottom: 5px;">🔬 מקצוע: מדעים</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: #1e293b;">{avg_pct_sci:.1f}% ביצוע מחוזי</div>
                <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">פוטנציאל תלמידים כולל: {total_students_sci:,}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    
    # ==================== חלק ב': בחירת מפקח וטבלאות ====================
    if 'מפקח' in df_dist.columns:
        sups = sorted(df_dist['מפקח'].dropna().unique())
        selected_supervisor = st.selectbox("👨‍🏫 בחר שם מפקח לקבלת מידע על מוסדותיו:", sups)
        
        if selected_supervisor:
            df_sup = df_dist[df_dist['מפקח'] == selected_supervisor]
            st.subheader(f"📋 רשימת מוסדות תחת פיקוחו/ה של: {selected_supervisor}")
            
            def color_picker(row):
                val = row['אחוז ביצוע']
                if val < 50.0:
                    color = '#ffccd5'
                elif val <= 85.0:
                    color = '#fef3c7'
                else:
                    color = '#d1fae5'
                return [f'background-color: {color}; color: black; font-weight: 500;' for _ in row]
            
            cols_to_show = ['מוסד', 'רשות', 'כיתה', 'מקבילה', 'פוטנציאל תלמידים', 'אחוז תלמידים שביצעו משימה אחת לפחות']
            available_cols = [c for c in cols_to_show if c in df_sup.columns] + ['אחוז ביצוע']
            
            if len(subjects_in_data) == 1 and subjects_in_data[0] == 'כללי':
                df_disp = df_sup[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                styled_df = df_disp.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                tab1, tab2 = st.tabs(["📐 מתמטיקה", "🔬 מדעים"])
                with tab1:
                    df_sup_math = df_sup[df_sup['מקצוע'] == 'מתמטיקה']
                    if not df_sup_math.empty:
                        df_disp_math = df_sup_math[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                        styled_math = df_disp_math.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                        st.dataframe(styled_math, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"לא נמצאו נתונים נפרדים במתמטיקה עבור המפקח {selected_supervisor}.")
                        
                with tab2:
                    df_sup_sci = df_sup[df_sup['מקצוע'] == 'מדעים']
                    if not df_sup_sci.empty:
                        df_disp_sci = df_sup_sci[available_cols].copy().sort_values(by='אחוז ביצוע', ascending=True)
                        styled_sci = df_disp_sci.style.apply(color_picker, axis=1).format({'אחוז ביצוע': '{:.1f}%'})
                        st.dataframe(styled_sci, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"לא נמצאו נתונים נפרדים במדעים עבור המפקח {selected_supervisor}.")
                    
            st.markdown("""
            <br>
            <div style="background-color: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: inline-block;">
                <strong style="color:#1d3557;">🎨 מקרא צבעים סטאטוס ביצוע ("אחוז תלמידים שביצעו משימה אחת לפחות"):</strong> &nbsp;&nbsp;
                <span style="background-color: #ffccd5; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🔴 0% - 50% (בסיכון גבוה)</span> &nbsp;&nbsp;
                <span style="background-color: #fef3c7; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🟡 50% - 85% (בטיפול)</span> &nbsp;&nbsp;
                <span style="background-color: #d1fae5; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🟢 85% ומעלה (מצוין)</span>
            </div>
            """, unsafe_allow_html=True)
