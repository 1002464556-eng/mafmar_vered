import streamlit as st
import pandas as pd
import numpy as np
import os

# ==================== הגדרות עמוד ותצוגה ====================
st.set_page_config(page_title="תלמידים אשר ביצעו את משימת המפמ\"ר", layout="wide", page_icon="📊")

# עיצוב מותאם אישית ליישור לימין (RTL) ומניעת חיתוך טקסט בטבלאות
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
    /* מניעת חיתוך או הסתרת טקסט בטבלאות Streamlit */
    .stDataFrame div table {
        direction: rtl !important;
        text-align: right !important;
    }
    .stDataFrame td, .stDataFrame th {
        white-space: normal !important;
        word-break: break-word !important;
        max-width: 300px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 תלמידים אשר ביצעו את משימת המפמ\"ר")
st.divider()

# ==================== פונקציות ניקוי ועיבוד נתונים ====================
def clean_percentage(val):
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
    if pd.isna(val):
        return 0
    val_str = str(val).replace(',', '').strip()
    try:
        return int(float(val_str))
    except:
        return 0

def process_single_sheet(df, target_col_name):
    """עיבוד שורות של לשונית בודדת ושקלול נתוני המוסד לרמה המקצועית"""
    df.columns = [str(c).strip() for c in df.columns]
    
    # סינון שורות סיכום ריקות
    if 'מוסד' in df.columns:
        df = df[~df['מוסד'].astype(str).str.contains('Totals|סיכום|total', na=False, case=False)]
        df = df[df['מוסד'].notna() & (df['מוסד'].astype(str).str.strip() != '')]
    else:
        return pd.DataFrame()
        
    df['פוטנציאל_נקי'] = df['פוטנציאל תלמידים'].apply(clean_numeric)
    
    # חיפוש עמודת אחוז הביצוע
    pct_col = 'אחוז תלמידים שביצעו משימה אחת לפחות'
    if pct_col not in df.columns:
        alt_cols = [c for c in df.columns if 'ביצעו משימה אחת' in c or 'אחוז' in c]
        pct_col = alt_cols[0] if alt_cols else df.columns[-1]
        
    df['אחוז_נקי'] = df[pct_col].apply(clean_percentage)
    df['תלמידים_שביצעו'] = (df['אחוז_נקי'] / 100.0) * df['פוטנציאל_נקי']
    
    # קיבוץ ושקלול לפי מוסד (כדי שאם מוסד מופיע בכמה כיתות בלשונית, הוא ישוקלל נכון)
    grouped = df.groupby('מוסד').agg({
        'מחוז': 'first',
        'מפקח': 'first',
        'רשות': 'first',
        'פוטנציאל_נקי': 'sum',
        'תלמידים_שביצעו': 'sum'
    }).reset_index()
    
    grouped[target_col_name] = (grouped['תלמידים_שביצעו'] / grouped['פוטנציאל_נקי'] * 100).fillna(0.0)
    return grouped[['מוסד', 'מחוז', 'מפקח', 'רשות', 'פוטנציאל_נקי', target_col_name]]

@st.cache_data(ttl=600)
def load_two_sheets_data():
    """טעינת קובץ האקסל וקריאת שתי הלשוניות בנפרד"""
    files = os.listdir('.')
    excel_files = [f for f in files if f.endswith('.xlsx') or f.endswith('.xls')]
    
    # אם אין אקסל, ננסה לבדוק קבצי CSV (במקרה שהעלית כקובצי CSV נפרדים)
    csv_files = [f for f in files if f.endswith('.csv')]
    
    df_math_agg = pd.DataFrame()
    df_sci_agg = pd.DataFrame()
    
    if excel_files:
        file_path = excel_files[0]
        try:
            excel_obj = pd.ExcelFile(file_path)
            # קריאת לשונית מתמטיקה
            if 'מתמטיקה' in excel_obj.sheet_names:
                df_m = pd.read_excel(file_path, sheet_name='מתמטיקה', dtype=str)
                df_math_agg = process_single_sheet(df_m, 'ביצוע מתמטיקה')
            
            # קריאת לשונית מדעים
            if 'מדעים' in excel_obj.sheet_names:
                df_s = pd.read_excel(file_path, sheet_name='מדעים', dtype=str)
                df_sci_agg = process_single_sheet(df_s, 'ביצוע מדעים')
        except Exception as e:
            return pd.DataFrame(), f"שגיאה בקריאת הלשוניות מקובץ האקסל: {str(e)}"
            
    # הגנת גיבוי במידה והקבצים הועלו כ-CSV נפרדים
    if df_math_agg.empty and df_sci_agg.empty and csv_files:
        for f in csv_files:
            for encoding in ['utf-8-sig', 'cp1255', 'utf-8']:
                try:
                    df_raw = pd.read_csv(f, encoding=encoding, dtype=str)
                    if 'מתמטיקה' in f:
                        df_math_agg = process_single_sheet(df_raw, 'ביצוע מתמטיקה')
                    elif 'מדע' in f:
                        df_sci_agg = process_single_sheet(df_raw, 'ביצוע מדעים')
                    break
                except:
                    continue

    if df_math_agg.empty and df_sci_agg.empty:
        return pd.DataFrame(), "לא נמצאו הלשוניות 'מתמטיקה' ו'מדעים' בתוך קובץ הנתונים."

    # מיזוג שתי הלשוניות לטבלה אחת אחודה לפי 'מוסד'
    if not df_math_agg.empty and not df_sci_agg.empty:
        # שימוש ב-Outer join כדי להבטיח שגם אם מוסד מופיע רק באחת מהן הוא לא ייעלם
        df_merged = pd.merge(
            df_math_agg[['מוסד', 'מחוז', 'מפקח', 'רשות', 'פוטנציאל_נקי', 'ביצוע מתמטיקה']],
            df_sci_agg[['מוסד', 'ביצוע מדעים', 'פוטנציאל_נקי']],
            on='מוסד', how='outer', suffixes=('_מתמטיקה', '_מדעים')
        )
        # השלמת ערכים חסרים
        df_merged['מחוז'] = df_merged['מחוז'].fillna(method='bfill').fillna(method='ffill')
        df_merged['מפקח'] = df_merged['מפקח'].fillna(method='bfill').fillna(method='ffill')
        df_merged['רשות'] = df_merged['רשות'].fillna('-')
        df_merged['פוטנציאל מתמטיקה'] = df_merged['פוטנציאל_נקי_מתמטיקה'].fillna(0).astype(int)
        df_merged['פוטנציאל מדעים'] = df_merged['פוטנציאל_נקי_מדעים'].fillna(0).astype(int)
        df_merged['ביצוע מתמטיקה'] = df_merged['ביצוע מתמטיקה'].fillna(0.0)
        df_merged['ביצוע מדעים'] = df_merged['ביצוע מדעים'].fillna(0.0)
        return df_merged, None
    else:
        # מקרה קצה שרק לשונית אחת קיימת או נקראה
        df_active = df_math_agg if not df_math_agg.empty else df_sci_agg
        if 'ביצוע מתמטיקה' not in df_active.columns: df_active['ביצוע מתמטיקה'] = 0.0
        if 'ביצוע מדעים' not in df_active.columns: df_active['ביצוע מדעים'] = 0.0
        df_active['פוטנציאל מתמטיקה'] = df_active['פוטנציאל_נקי']
        df_active['פוטנציאל מדעים'] = df_active['פוטנציאל_נקי']
        return df_active, None

# ==================== טעינה ועיבוד ====================
df_main, error_msg = load_two_sheets_data()

if error_msg:
    st.error(f"❌ {error_msg}")
    st.stop()

# ==================== חלק א': פילוח מחוזי ושקלול נפרד ומדויק ====================
if 'מחוז' in df_main.columns:
    districts = sorted(df_main['Mחוז'].dropna().unique()) if 'Mחוז' in df_main.columns else sorted(df_main['מחוז'].dropna().unique())
    selected_district = st.selectbox("🎯 בחר מחוז לצפייה:", districts)
    
    df_dist = df_main[df_main['מחוז'] == selected_district]
    st.markdown(f"### נתונים כלליים ומדדים עבור מחוז: **{selected_district}**")
    
    # שקלול מחוזי נפרד ומדויק למתמטיקה ולמדעים
    sum_pot_math = df_dist['פוטנציאל מתמטיקה'].sum()
    avg_math = ((df_dist['ביצוע מתמטיקה'] / 100.0) * df_dist['פוטנציאל מתמטיקה']).sum() / sum_pot_math * 100 if sum_pot_math > 0 else 0.0
    
    sum_pot_sci = df_dist['פוטנציאל מדעים'].sum()
    avg_sci = ((df_dist['ביצוע מדעים'] / 100.0) * df_dist['פוטנציאל מדעים']).sum() / sum_pot_sci * 100 if sum_pot_sci > 0 else 0.0
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #E63946; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div style="font-size: 1.1rem; font-weight: bold; color: #E63946; margin-bottom: 5px;">📐 שקלול מחוזי - מתמטיקה</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #1e293b;">{avg_math:.1f}% ביצוע</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">פוטנציאל תלמידים כולל במחוז: {int(sum_pot_math):,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div style="background-color: white; border-right: 5px solid #1D3557; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div style="font-size: 1.1rem; font-weight: bold; color: #1D3557; margin-bottom: 5px;">🔬 שקלול מחוזי - מדעים</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #1e293b;">{avg_sci:.1f}% ביצוע</div>
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 5px;">פוטנציאל תלמידים כולל במחוז: {int(sum_pot_sci):,}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # ==================== חלק ב': הצגת טבלה מרוכזת לפי מפקח ====================
    if 'מפקח' in df_dist.columns:
        sups = sorted(df_dist['מפקח'].dropna().unique())
        selected_supervisor = st.selectbox("👨‍🏫 בחר שם מפקח לקבלת מידע על מוסדותיו:", sups)
        
        if selected_supervisor:
            df_sup = df_dist[df_dist['מפקח'] == selected_supervisor].copy()
            st.subheader(f"📋 סטטוס ביצוע מוסדי משולב - מפקח: {selected_supervisor}")
            
            # הכנת העמודות לתצוגה ברורה
            df_display = df_sup[['מוסד', 'רשות', 'פוטנציאל מתמטיקה', 'ביצוע מתמטיקה', 'פוטנציאל מדעים', 'ביצוע מדעים']].copy()
            df_display = df_display.sort_values(by='ביצוע מתמטיקה', ascending=True)
            
            # פונקציה לצביעת משבצות המקצועות בלבד (השורה נשארת לבנה)
            def style_only_subject_cells(data):
                # יצירת מטריצה ריקה (ללא עיצוב כברירת מחדל) עבור כל התאים
                style_df = pd.DataFrame('', index=data.index, columns=data.columns)
                
                # החלת צבע רמזור רק על שתי העמודות של המקצועות
                for col in ['ביצוע מתמטיקה', 'ביצוע מדעים']:
                    for idx in data.index:
                        val = data.loc[idx, col]
                        if val < 50.0:
                            bg = '#ffccd5' # אדום לסיכון
                        elif val <= 85.0:
                            bg = '#fef3c7' # צהוב בטיפול
                        else:
                            bg = '#d1fae5' # ירוק מצוין
                        style_df.loc[idx, col] = f'background-color: {bg}; color: black; font-weight: bold; text-align: center;'
                return style_df

            # החלת העיצובים והגדרת הפורמט של האחוזים
            styled_table = df_display.style.apply(style_only_subject_cells, axis=None).format({
                'ביצוע מתמטיקה': '{:.1f}%',
                'ביצוע מדעים': '{:.1f}%',
                'פוטנציאל מתמטיקה': '{:,}',
                'פוטנציאל מדעים': '{:,}'
            })
            
            # תצוגה רחבה המונעת מהטקסט להיחתך
            st.dataframe(styled_table, use_container_width=True, hide_index=True)

            # מקרא צבעים
            st.markdown("""
            <br>
            <div style="background-color: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: inline-block;">
                <strong style="color:#1d3557;">🎨 מקרא רמזור למשבצות המקצועות:</strong> &nbsp;&nbsp;
                <span style="background-color: #ffccd5; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🔴 0% - 50% (סיכון)</span> &nbsp;&nbsp;
                <span style="background-color: #fef3c7; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🟡 50% - 85% (בטיפול)</span> &nbsp;&nbsp;
                <span style="background-color: #d1fae5; padding: 4px 10px; border-radius: 4px; color: black; font-weight: bold;">🟢 85% ומעלה (מצוין)</span>
            </div>
            """, unsafe_allow_html=True)
