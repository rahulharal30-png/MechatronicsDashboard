# ==============================================================
# app.py — Mechatronics Power BI Edition (Visuals v3.7 - Final Polish)
# ==============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re
import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Mechatronics BI", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar collapsed by default
)

# 2. LOAD CSS
def load_css():
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Style file not found. Ensure 'assets/style.css' exists.")

load_css()

# --- THEME ENGINE ---
def theme_plotly(fig, height=300):
    fig.update_layout(
        font_family="Inter, Segoe UI, sans-serif",
        font_color="#4b5563",
        title_font_size=14,
        title_font_family="Inter, Segoe UI, sans-serif",
        title_font_color="#111827",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=10, l=10, r=10),
        height=height,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
    )
    fig.update_xaxes(showgrid=False, linecolor="#e5e7eb", automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor="#f3f4f6", automargin=True)
    return fig

# ------------------------------------------------------------
# 3. SIDEBAR
# ------------------------------------------------------------
st.sidebar.title("📦 Mechatronics")

if st.sidebar.button("🔥 Clear Cache & Reload", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["Inventory Overview", "Delivery Tracking", "Project Explorer"])

# ------------------------------------------------------------
# 4. DATA ENGINE (v8 - Final Clean)
# ------------------------------------------------------------
@st.cache_data
def load_data_v8():
    file_path = "Mechatronics Project Parts_Data.xlsx"
    if not Path(file_path).exists(): return None, None, None

    try:
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        
        # Load Sheets
        comp_sheet = next((s for s in xls.sheet_names if "Component" in s), xls.sheet_names[0])
        df_comp = pd.read_excel(xls, sheet_name=comp_sheet)
        
        set_sheet = next((s for s in xls.sheet_names if "Set" in s and "Delivery" in s), None)
        if not set_sheet: set_sheet = next((s for s in xls.sheet_names if "Delivery" in s), None)
        df_sets = pd.read_excel(xls, sheet_name=set_sheet) if set_sheet else pd.DataFrame()

        proj_sheet = next((s for s in xls.sheet_names if "Project" in s and "Considered" in s), None)
        df_proj = pd.read_excel(xls, sheet_name=proj_sheet) if proj_sheet else pd.DataFrame()

        # Clean Headers
        for df in [df_comp, df_sets, df_proj]:
            if not df.empty:
                df.columns = [c.strip() for c in df.columns]

        # --- SMART CLEANER ---
        def clean(df):
            if df.empty: return df
            
            # Identify ID columns to force UPPERCASE for matching
            id_cols = [c for c in df.columns if any(x in c.lower() for x in ['no', 'id', 'code', 'mfg'])]

            for col in df.columns:
                if "link" in col.lower(): continue 
                
                # 1. Force String & Strip
                s = df[col].astype(str).str.strip()
                
                # 2. Fix Float Strings (Global fix: "2095.0" -> "2095")
                s = s.str.replace(r'\.0$', '', regex=True)
                
                # 3. Replace Junk with clean dash (Visual Fix)
                # This ensures "nan", "None", etc become "-" instead of "Undefined"
                s = s.replace(r'(?i)^(nan|none|unknown|undefined|null|nat)$', '-', regex=True)
                
                # 4. Case Standardization
                if col in id_cols:
                    s = s.str.upper() # IDs -> UPPERCASE
                else:
                    s = s.str.title() # Text -> Title Case
                
                df[col] = s
            
            # 5. Brand Standardization
            brand_map = {
                "DFROBOT": "DFRobot", "DFR": "DFRobot", "ADAFRUIT": "Adafruit", 
                "POLOLU": "Pololu", "SPARKFUN": "SparkFun", "ARDUINO": "Arduino", 
                "ESPRESSIF": "Espressif", "SEEED": "Seeed Studio"
            }
            for c in df.columns:
                if c.lower() in ["mfg", "manufacturer", "brand"]:
                    df[c] = df[c].replace(brand_map)
                    
            return df

        return clean(df_comp), clean(df_sets), clean(df_proj)

    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return None, None, None

df_components, df_sets, df_projects = load_data_v8()

if df_components is None:
    st.error("❌ File not found. Please upload 'Mechatronics Project Parts_Data.xlsx'")
    st.stop()
else:
    st.sidebar.caption(f"DB Connected: {datetime.datetime.now().strftime('%H:%M')}")

# --- HELPERS ---
def get_col(df, candidates):
    if df is None or df.empty: return None
    col_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_map: return col_map[cand.lower()]
    return None

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

def kpi_card(label, value, color="#111827"):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color: {color};">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------
# DASHBOARD 1: INVENTORY OVERVIEW
# ------------------------------------------------------------
if page == "Inventory Overview":
    
    c_cat = get_col(df_components, ["Category"])
    c_status = get_col(df_components, ["Status"])
    c_brand = get_col(df_components, ["Mfg", "Manufacturer", "Brand"])
    c_sub1 = get_col(df_components, ["SubCategory"])
    c_sub2 = get_col(df_components, ["SubCategory2"])
    
    c_mfg_no = get_col(df_components, ["MfgNo", "Mfg No", "PartNo", "Part Number"])
    c_name = get_col(df_components, ["Name", "Description", "Component Name"])
    c_link = get_col(df_components, ["Link", "Url"])

    st.sidebar.header("🔍 Filters")
    df_filtered = df_components.copy()
    filters_active = False

    if c_status:
        opts = sorted(list(df_components[c_status].unique()))
        sel_stat = st.sidebar.multiselect("Status", opts, default=opts)
        if len(sel_stat) < len(opts): filters_active = True
        if sel_stat: df_filtered = df_filtered[df_filtered[c_status].isin(sel_stat)]
        
    if c_cat:
        opts = sorted(list(df_components[c_cat].unique()))
        sel_cat = st.sidebar.multiselect("Category", opts, default=opts)
        if len(sel_cat) < len(opts): filters_active = True
        if sel_cat: df_filtered = df_filtered[df_filtered[c_cat].isin(sel_cat)]

    c_title, c_search = st.columns([1, 1])
    with c_title: st.markdown("## 🏭 Inventory Cockpit")
    with c_search:
        search_inv = st.text_input("Search", placeholder="Search Mfg No, Name, or Brand...", label_visibility="collapsed")
        if search_inv:
            search_term = search_inv.strip()
            mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            df_filtered = df_filtered[mask]
            filters_active = True 

    total = len(df_filtered)
    avail = df_filtered[c_status].str.contains("Available", case=False).sum() if c_status else 0
    pct = int((avail/total)*100) if total > 0 else 0
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Parts Found", total)
    with k2: kpi_card("Availability", f"{pct}%", "#16a34a" if pct > 50 else "#dc2626")
    with k3: kpi_card("Categories", df_filtered[c_cat].nunique() if c_cat else 0)
    with k4: kpi_card("Manufacturers", df_filtered[c_brand].nunique() if c_brand else 0)

    st.markdown("<br>", unsafe_allow_html=True)

    c_left, c_right = st.columns([1, 2])
    with c_left:
        st.markdown('<div class="card-container"><div class="chart-title">Status Overview</div>', unsafe_allow_html=True)
        if c_status and not df_filtered.empty:
            stat_counts = df_filtered[c_status].value_counts().reset_index()
            stat_counts.columns = ["Status", "Count"]
            fig = px.pie(stat_counts, names="Status", values="Count", hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(theme_plotly(fig), use_container_width=True)
        else: st.info("No data.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="card-container"><div class="chart-title">Category Distribution</div>', unsafe_allow_html=True)
        if c_cat and not df_filtered.empty:
            cat_counts = df_filtered[c_cat].value_counts().reset_index().head(12)
            cat_counts.columns = ["Category", "Count"]
            fig = px.bar(cat_counts, x="Category", y="Count", text="Count", color="Count", color_continuous_scale="Blues")
            st.plotly_chart(theme_plotly(fig), use_container_width=True)
        else: st.info("No data.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-container"><div class="chart-title">Top Manufacturers</div>', unsafe_allow_html=True)
    if c_brand and not df_filtered.empty:
        brand_data = df_filtered[c_brand].value_counts().reset_index().head(25)
        brand_data.columns = ["Brand", "Count"]
        fig = px.treemap(brand_data, path=["Brand"], values="Count", color="Count", color_continuous_scale="Mint")
        st.plotly_chart(theme_plotly(fig, height=350), use_container_width=True)
    else: st.info("No data.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-container"><div class="chart-title">Data Explorer (Sunburst)</div>', unsafe_allow_html=True)
    if c_cat and c_sub1 and not df_filtered.empty:
        df_sun = df_filtered.copy()
        df_sun[c_cat] = df_sun[c_cat].replace("-", "Unknown") 
        path = [c_cat, c_sub1]
        if c_sub2 and df_sun[c_sub2].notna().any():
            df_sun[c_sub2] = df_sun[c_sub2].fillna("-")
            path.append(c_sub2)
        fig = px.sunburst(df_sun, path=path, color=c_cat, color_discrete_sequence=px.colors.qualitative.Prism, maxdepth=3)
        st.plotly_chart(theme_plotly(fig, height=600), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if filters_active:
        st.markdown('<div class="card-container"><div class="chart-title">📋 Component Details</div>', unsafe_allow_html=True)
        if not df_filtered.empty:
            cols_to_show = [c for c in [c_mfg_no, c_brand, c_name, c_cat, c_status, c_link] if c]
            st.dataframe(df_filtered[cols_to_show], hide_index=True, use_container_width=True)
        else: st.warning("No components match your filters.")
        st.markdown('</div>', unsafe_allow_html=True)
    else: st.caption("👇 *Use the Search bar or Sidebar Filters to see the detailed component list.*")

# ------------------------------------------------------------
# DASHBOARD 2: DELIVERY TRACKING
# ------------------------------------------------------------
elif page == "Delivery Tracking":
    
    s_set = get_col(df_sets, ["Set No", "Set"])
    s_status = get_col(df_sets, ["Final Status", "Status"])
    s_link = get_col(df_sets, ["Link", "Url"])
    s_name = get_col(df_sets, ["xDesign Name", "Name", "Description", "Component Name"])
    s_mfg = get_col(df_sets, ["Mfg No", "MfgNo", "Part No"])
    
    if df_sets.empty or not s_set or not s_status:
        st.error("❌ Delivery Data Missing.")
        st.stop()
        
    st.markdown("## 🚚 Delivery Tracking")
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        all_sets = sorted(list(df_sets[s_set].unique()), key=natural_sort_key)
        selected_sets = st.multiselect("Select Set(s)", all_sets, placeholder="Choose specific sets (e.g. Set 1)")
    with f2:
        search_del = st.text_input("Text Search", placeholder="Search Mfg No, Name, or Status...", label_visibility="visible")
    st.markdown('</div>', unsafe_allow_html=True)

    df_view = df_sets.copy()
    is_filtered = False

    if selected_sets:
        df_view = df_view[df_view[s_set].isin(selected_sets)]
        is_filtered = True
    
    if search_del:
        target_cols = [c for c in [s_name, s_mfg, s_status] if c] 
        mask = df_view[target_cols].astype(str).apply(lambda x: x.str.contains(search_del, case=False)).any(axis=1)
        df_view = df_view[mask]
        is_filtered = True

    total = len(df_view)
    released = df_view[s_status].str.contains("Released", case=False, na=False).sum()
    pending = total - released
    pct_rel = int((released/total)*100) if total > 0 else 0
    
    k1, k2, k3 = st.columns(3)
    with k1: kpi_card("Items Found", total)
    with k2: kpi_card("Released", released, "#16a34a")
    with k3: kpi_card("Pending", pending, "#dc2626")
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="card-container"><div class="chart-title">Readiness Gauge</div>', unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = pct_rel, gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#3b82f6"}}))
        st.plotly_chart(theme_plotly(fig_gauge, height=250), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card-container"><div class="chart-title">Set Composition</div>', unsafe_allow_html=True)
        if not df_view.empty:
            df_stack = df_view.groupby([s_set, s_status]).size().reset_index(name="Count")
            df_stack = df_stack.sort_values(by=s_set, key=lambda col: col.map(lambda x: natural_sort_key(x)))
            colors = {"Released": "#22c55e", "Backorder": "#ef4444", "Split": "#eab308", "Out Of Stock": "#dc2626"}
            fig = px.bar(df_stack, x=s_set, y="Count", color=s_status, color_discrete_map=colors)
            st.plotly_chart(theme_plotly(fig, height=280), use_container_width=True)
        else: st.info("No data matches current filter.")
        st.markdown('</div>', unsafe_allow_html=True)

    if is_filtered:
        st.markdown('<div class="card-container"><div class="chart-title">📋 Complete Manifest</div>', unsafe_allow_html=True)
        if not df_view.empty:
            display_cols = [c for c in [s_set, s_mfg, s_name, s_status, s_link] if c is not None]
            st.dataframe(df_view[display_cols], hide_index=True, use_container_width=True, height=600)
        else: st.warning("No items match your search criteria.")
        st.markdown('</div>', unsafe_allow_html=True)
    else: st.caption("👇 *Select a Set or Search to view individual line items.*")

# ------------------------------------------------------------
# DASHBOARD 3: PROJECT EXPLORER (With Strict Type Fixes)
# ------------------------------------------------------------
elif page == "Project Explorer":
    
    st.markdown("## 🚀 Project Explorer")
    if df_projects is None or df_projects.empty:
        st.error("❌ 'Projects Considered' sheet not found.")
        st.stop()

    p_name_col = df_projects.columns[0]
    comp_cols = [c for c in df_projects.columns if "Component" in c]

    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    all_projects = sorted(df_projects[p_name_col].astype(str).unique())
    selected_proj = st.selectbox("Select a Project to View Bill of Materials (BOM)", all_projects, index=None, placeholder="Choose a Project...")
    st.markdown('</div>', unsafe_allow_html=True)

    if selected_proj:
        proj_row = df_projects[df_projects[p_name_col] == selected_proj]
        bom = proj_row.melt(id_vars=[p_name_col], value_vars=comp_cols, value_name="MfgNo").dropna()
        
        # KEY FIX: The main cleaning function ALREADY upper-cased everything in df_proj
        # So we just need to ensure we don't have junk
        bom = bom[bom["MfgNo"].str.len() > 1]
        bom = bom[~bom["MfgNo"].isin(["-", "UNKNOWN", "NAN", "NONE"])]
        
        c_mfg_no = get_col(df_components, ["MfgNo", "Mfg No", "PartNo", "Part Number"])
        
        if c_mfg_no:
            # df_components is ALSO already upper-cased by load_data_v8
            df_bom = pd.merge(bom, df_components, left_on="MfgNo", right_on=c_mfg_no, how="left")
            
            # FILL REMAINING GAPS WITH DASH (Clean Look)
            df_bom = df_bom.fillna("-")
            
            total_parts = len(df_bom)
            c_status = get_col(df_components, ["Status"])
            
            if c_status in df_bom.columns:
                in_stock = df_bom[c_status].str.contains("Available", case=False, na=False).sum()
                missing = total_parts - in_stock
                readiness = int((in_stock/total_parts)*100) if total_parts > 0 else 0
            else:
                readiness = 0
                missing = total_parts

            k1, k2, k3 = st.columns(3)
            with k1: kpi_card("Total Components", total_parts)
            with k2: kpi_card("Readiness", f"{readiness}%", "#16a34a" if readiness == 100 else "#eab308")
            with k3: kpi_card("Missing / Issues", missing, "#dc2626" if missing > 0 else "#16a34a")
            st.markdown("<br>", unsafe_allow_html=True)

            c_cat = get_col(df_components, ["Category"])
            vc1, vc2 = st.columns([1, 2])
            
            with vc1:
                st.markdown('<div class="card-container"><div class="chart-title">Stock Status</div>', unsafe_allow_html=True)
                if c_status in df_bom.columns:
                    status_data = df_bom[c_status].value_counts().reset_index()
                    status_data.columns = ["Status", "Count"]
                    fig_stat = px.pie(status_data, names="Status", values="Count", hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(theme_plotly(fig_stat, height=300), use_container_width=True)
                else: st.info("Status info unavailable")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with vc2:
                st.markdown('<div class="card-container"><div class="chart-title">Component Composition</div>', unsafe_allow_html=True)
                if c_cat and c_cat in df_bom.columns:
                    cat_data = df_bom[c_cat].replace("-", "Uncategorized").value_counts().reset_index().head(10)
                    cat_data.columns = ["Category", "Count"]
                    fig_cat = px.bar(cat_data, x="Count", y="Category", text="Count", orientation='h', color="Count", color_continuous_scale="Blues")
                    fig_cat.update_layout(yaxis=dict(autorange="reversed"), xaxis_title=None, yaxis_title=None)
                    st.plotly_chart(theme_plotly(fig_cat, height=300), use_container_width=True)
                else: st.info("Category info unavailable")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card-container"><div class="chart-title">📋 Bill of Materials</div>', unsafe_allow_html=True)
            c_name = get_col(df_components, ["Name", "Description", "Component Name"])
            c_link = get_col(df_components, ["Link", "Url"])
            disp_cols = ["MfgNo"]
            if c_name: disp_cols.append(c_name)
            if c_status: disp_cols.append(c_status)
            if c_link: disp_cols.append(c_link)
            
            final_cols = [c for c in disp_cols if c in df_bom.columns]
            st.dataframe(df_bom[final_cols], hide_index=True, use_container_width=True, height=500)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Could not link Project Data to Inventory. 'MfgNo' column missing in Inventory.")
    else: st.info("👆 Please select a project above to see its components.")