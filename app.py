import streamlit as st
import pandas as pd
import os
import base64

# ==================== הגדרות עמוד ====================
st.set_page_config(page_title="ישראל ראלית - משימות מודל", layout="wide", page_icon="🇮🇱")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    * { direction: rtl; }
    .math-title { color: #E63946; font-weight: bold; }
    .sci-title { color: #1D3557; font-weight: bold; }
    div[data-testid="metric-container"] {
        background-color: white;
        border-right: 5px solid #1D3557;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ==================== פונקציות עיבוד נתונים ====================
def safe_read(f):
    try:
        if isinstance(f, str):
            if f.endswith('.xlsx'): return pd.read_excel(f)
            return pd.read_csv(f, encoding='utf-8-sig', dtype=str)
        else: # תמיכה בקבצים מועלים דרך הממשק
            if f.name.endswith('.xlsx'): return pd.read_excel(f)
            return pd.read_csv(f, encoding='utf-8-sig', dtype=str)
    except:
        try: 
            if isinstance(f, str):
                return pd.read_csv(f, encoding='cp1255', dtype=str)
            else:
                return pd.read_csv(f, encoding='cp1255', dtype=str)
        except: 
            return pd.DataFrame()

def get_all_data(uploaded_files=None):
    # שילוב קבצים מהתיקייה המקומית וקבצים שהועלו בדפדפן
    local_files = os.listdir('.') if os.path.exists('.') else []
    
    # מיון קובצי החרגה
    excluded = []
    # חפש בקבצים מקומיים
    exc_f = next((f for f in local_files if 'להחרגה' in f), None)
    if exc_f:
        df_ex = safe_read(exc_f)
        for col in df_ex.columns:
            extracted = df_ex[col].astype(str).str.extract(r'(\d{6})')[0].dropna().tolist()
            if extracted: excluded.extend(extracted)
            
    # חפש בקבצים שהועלו בממשק
    if uploaded_files:
        for f in uploaded_files:
            if 'להחרגה' in f.name:
                df_ex = safe_read(f)
                for col in df_ex.columns:
                    extracted = df_ex[col].astype(str).str.extract(r'(\d{6})')[0].dropna().tolist()
                    if extracted: excluded.extend(extracted)

    model_list = []
    # קריאת קבצי מודל מקומיים
    for f in [f for f in local_files if 'מודל' in f]:
        df = safe_read(f)
        if not df.empty: model_list.append((f, df))
    # קריאת קבצי מודל מהדפדפן
    if uploaded_files:
        for f in uploaded_files:
            if 'מודל' in f.name:
                df = safe_read(f)
                if not df.empty: model_list.append((f.name, df))

    processed_model_list = []
    for fname, df in model_list:
        col_school = next((c for c in df.columns if 'מוסד' in c and 'סמל' not in c), None)
        col_dist = next((c for c in df.columns if 'מחוז' in c), None)
        col_sup = next((c for c in df.columns if 'מפקח' in c), None)
        col_avg = next((c for c in df.columns if 'ממוצע' in c), None)
        
        if not col_school or not col_avg: continue
        
        temp = pd.DataFrame()
        temp['סמל מוסד'] = df[col_school].astype(str).str.extract(r'(\d{6})')[0]
        temp['מוסד'] = df[col_school].astype(str).str.replace(r'^\d{6}\s*-\s*', '', regex=True)
        temp['מחוז תקשוב'] = df[col_dist].astype(str).str.strip() if col_dist else 'לא ידוע'
        temp['שם מפקח'] = df[col_sup].astype(str).str.strip() if col_sup else 'לא ידוע'
        temp['תחום'] = 'מתמטיקה' if 'מתמטיקה' in fname else 'מדעים'
        temp['ממוצע משימות'] = pd.to_numeric(df[col_avg], errors='coerce').fillna(0).round(2)
        
        temp = temp[temp['סמל מוסד'].notna() & ~temp['סמל מוסד'].isin(excluded)]
        processed_model_list.append(temp)

    urg_list = []
    # קריאת קבצי תפעולי מקומיים
    for f in [f for f in local_files if 'תפעולי' in f]:
        df = safe_read(f)
        if not df.empty: urg_list.append((f, df))
    # קריאת קבצי תפעולי מהדפדפן
    if uploaded_files:
        for f in uploaded_files:
            if 'תפעולי' in f.name:
                df = safe_read(f)
                if not df.empty: urg_list.append((f.name, df))

    processed_urg_list = []
    for fname, df in urg_list:
        col_pot = next((c for c in df.columns if 'פוטנציאל' in c), None)
        col_perf = next((c for c in df.columns if 'שביצעו' in c and 'אחוז' not in c), None)
        col_sup = next((c for c in df.columns if 'מפקח' in c), None)
        col_school = next((c for c in df.columns if 'שם מוסד' in c or ('מוסד' in c and 'סמל' not in c)), None)
        col_symbol = next((c for c in df.columns if 'סמל מוסד' in c), None)
        
        if not col_pot or not col_perf: continue

        df['סמל'] = df[col_symbol].astype(str) if col_symbol else df[col_school].astype(str).str.extract(r'(\d{6})')[0]
        df['שם'] = df[col_school].astype(str).str.replace(r'^\d{6}\s*-\s*', '', regex=True)
        df['pot'] = pd.to_numeric(df[col_pot], errors='coerce').fillna(0)
        df['perf'] = pd.to_numeric(df[col_perf], errors='coerce').fillna(0)
        
        df['אחוז'] = (df['perf'] / df['pot'] * 100).fillna(0)
        urgent = df[df['אחוז'] < 50].copy()
        
        if not urgent.empty:
            res = pd.DataFrame()
            res['סמל מוסד'] = urgent['סמל']
            res['מוסד'] = urgent['שם']
            res['שם מפקח'] = urgent[col_sup].astype(str).str.strip() if col_sup else 'לא ידוע'
            res['מחוז תקשוב'] = urgent[next((c for c in df.columns if 'מחוז' in c), 'District')].astype(str).str.strip()
            res['תחום'] = 'מתמטיקה' if 'מתמטיקה' in fname else 'מדעים'
            processed_urg_list.append(res)

    all_model = pd.concat(processed_model_list).drop_duplicates(subset=['סמל מוסד', 'תחום'], keep='last') if processed_model_list else pd.DataFrame()
    all_urg = pd.concat(processed_urg_list).drop_duplicates(subset=['סמל מוסד', 'תחום'], keep='last') if processed_urg_list else pd.DataFrame()
    
    if not all_model.empty:
        all_model['שם מפקח'] = all_model['שם מפקח'].str.strip()
        all_model['מחוז תקשוב'] = all_model['מחוז תקשוב'].str.strip()
    if not all_urg.empty:
        all_urg['שם מפקח'] = all_urg['שם מפקח'].str.strip()
        all_urg['מחוז תקשוב'] = all_urg['מחוז תקשוב'].str.strip()
        
    return all_model, all_urg

# ==================== פונקציה לייצור טבלת HTML ====================
def render_html_table(df, domain=None, is_urgent=False):
    if df.empty:
        st.success("אין מוסדות להצגה.")
        return

    df_display = df.copy()
    if not is_urgent and 'ממוצע משימות' in df_display.columns:
        df_display['ממוצע משימות'] = df_display['ממוצע משימות'].map('{:.2f}'.format)

    styler = df_display.style.hide(axis="index")

    if not is_urgent:
        def row_color(row):
            try:
                val = float(row['ממוצע משימות'])
            except:
                val = 0
            limit_red = 5 if domain == 'מתמטיקה' else 2
            limit_green = 12 if domain == 'מתמטיקה' else 6
            color = '#fad2e1' if val < limit_red else ('#fefae0' if val < limit_green else '#d8f3dc')
            return [f'background-color: {color}; color: black;' for _ in row]
        styler = styler.apply(row_color, axis=1)

    styler = styler.set_properties(subset=['סמל מוסד'], **{
        'text-align': 'right', 
        'width': '80px', 
        'min-width': '80px', 
        'white-space': 'nowrap'
    })
    
    styler = styler.set_properties(subset=['מוסד'], **{
        'text-align': 'right'
    })
    
    if not is_urgent and 'ממוצע משימות' in df_display.columns:
        styler = styler.set_properties(subset=['ממוצע משימות'], **{
            'text-align': 'right', 
            'width': '90px', 
            'min-width': '90px'
        })

    styler.set_table_styles([
        {'selector': 'table', 'props': [('width', '100%'), ('direction', 'rtl'), ('border-collapse', 'collapse'), ('margin-bottom', '20px')]},
        {'selector': 'th', 'props': [('background-color', '#1D3557'), ('color', 'white'), ('padding', '8px'), ('text-align', 'right')]},
        {'selector': 'td', 'props': [('padding', '8px'), ('border-bottom', '1px solid #ddd')]}
    ])

    st.markdown(styler.to_html(), unsafe_allow_html=True)

# ==================== ממשק משתמש ====================
st.title("ישראל ראלית - דשבורד מודל ז'")
st.divider()

# אפשרות להעלאת קבצים ישירות מהדפדפן
st.sidebar.header("📂 טעינת קבצי נתונים")
uploaded_files = st.sidebar.file_uploader("העלה קבצי אקסל או CSV (מודל / תפעולי / להחרגה):", accept_multiple_files=True)

df_model, df_urgent = get_all_data(uploaded_files)

if df_model.empty:
    st.warning("🔄 אנא העלה קבצים המכילים את המילה 'מודל' או 'תפעולי' בסרגל הצד כדי להציג את הנתונים.")
    st.stop()

districts = sorted([d for d in df_model['מחוז תקשוב'].unique() if pd.notna(d) and d != 'לא ידוע'])
district = st.sidebar.selectbox("בחר מחוז:", districts) if districts else ""

if district:
    df_dist = df_model[df_model['מחוז תקשוב'] == district]
    sups = sorted([s for s in df_dist['שם מפקח'].unique() if pd.notna(s) and s != 'לא ידוע'])
    supervisor = st.selectbox("בחר מפקח/ת:", sups) if sups else ""

    col1, col2 = st.columns(2)
    with col1:
        math_avg = df_dist[df_dist['תחום'] == 'מתמטיקה']['ממוצע משימות'].mean()
        st.markdown("<h3 class='math-title'>📐 מתמטיקה</h3>", unsafe_allow_html=True)
        st.metric("ממוצע משימות מחוזי", f"{math_avg:.2f}" if pd.notna(math_avg) else "0.00")
    with col2:
        sci_avg = df_dist[df_dist['תחום'] == 'מדעים']['ממוצע משימות'].mean()
        st.markdown("<h3 class='sci-title'>🔬 מדעים</h3>", unsafe_allow_html=True)
        st.metric("ממוצע משימות מחוזי", f"{sci_avg:.2f}" if pd.notna(sci_avg) else "0.00")
    
    st.divider()

    if supervisor:
        df_sup = df_dist[df_dist['שם מפקח'] == supervisor]
        
        st.subheader(f"ביצועי מוסדות - {supervisor}")
        tab1, tab2 = st.tabs(["מתמטיקה", "מדעים"])
        
        with tab1:
            data_m = df_sup[df_sup['תחום'] == 'מתמטיקה'][['סמל מוסד', 'מוסד', 'ממוצע משימות']].sort_values('ממוצע משימות', ascending=False)
            render_html_table(data_m, domain='מתמטיקה', is_urgent=False)
            
        with tab2:
            data_s = df_sup[df_sup['תחום'] == 'מדעים'][['סמל מוסד', 'מוסד', 'ממוצע משימות']].sort_values('ממוצע משימות', ascending=False)
            render_html_table(data_s, domain='מדעים', is_urgent=False)

        st.divider()
        st.header("🚨 מוקדי התערבות דחופים (פחות מ-50% ביצוע)")
        
        if not df_urgent.empty:
            df_urg_filtered = df_urgent[(df_urgent['מחוז תקשוב'] == district) & (df_urgent['שם מפקח'] == supervisor)]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### מתמטיקה")
                urg_m = df_urg_filtered[df_urg_filtered['תחום'] == 'מתמטיקה'][['סמל מוסד', 'מוסד']]
                render_html_table(urg_m, is_urgent=True)
                
            with c2:
                st.markdown("### מדעים")
                urg_s = df_urg_filtered[df_urg_filtered['תחום'] == 'מדעים'][['סמל מוסד', 'מוסד']]
                render_html_table(urg_s, is_urgent=True)