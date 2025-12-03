# ==============================================================
# app.py — Mechatronics Power BI Edition
# ==============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Mechatronics BI", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. LOAD CSS
def load_css():
    css_path = Path("assets/style.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
load_css()

# ------------------------------------------------------------
# 3. SIDEBAR
# ------------------------------------------------------------
st.sidebar.title("📦 Mechatronics")

if st.sidebar.button("🔄 Hard Refresh", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["Inventory Overview", "Delivery Tracking"])

# ------------------------------------------------------------
# 4. DATA ENGINE
# ------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "Mechatronics Project Parts_Data.xlsx"
    if not Path(file_path).exists(): return None, None

    try:
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        
        # Smart Sheet Finding
        comp_sheet = next((s for s in xls.sheet_names if "Component" in s), xls.sheet_names[0])
        df_comp = pd.read_excel(xls, sheet_name=comp_sheet)
        
        set_sheet = next((s for s in xls.sheet_names if "Set" in s and "Delivery" in s), None)
        if not set_sheet: set_sheet = next((s for s in xls.sheet_names if "Delivery" in s), None)
        df_sets = pd.read_excel(xls, sheet_name=set_sheet) if set_sheet else pd.DataFrame()

        # Clean Headers
        df_comp.columns = [c.strip() for c in df_comp.columns]
        if not df_sets.empty: df_sets.columns = [c.strip() for c in df_sets.columns]

        # Cleaning Logic
        def clean(df):
            if df.empty: return df
            for col in df.select_dtypes(include=['object']):
                if "link" not in col.lower():
                    df[col] = df[col].astype(str).str.strip().str.title()
                    df[col] = df[col].replace({"Nan": "Unknown", "nan": "Unknown", "None": "Unknown"})
            
            brand_map = {
                "Dfrobot": "DFRobot", "Dfr": "DFRobot", 
                "Adafruit": "Adafruit", "Pololu": "Pololu", 
                "Sparkfun": "SparkFun", "Arduino": "Arduino", 
                "Espressif": "Espressif", "Seeed": "Seeed Studio",
                "Stmicroelectronics": "STMicroelectronics"
            }
            for c in df.columns:
                if c.lower() in ["mfg", "manufacturer", "brand"]:
                    df[c] = df[c].replace(brand_map)
            return df

        return clean(df_comp), clean(df_sets)

    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return None, None

df_components, df_sets = load_data()

if df_components is None:
    st.error("❌ File not found. Please upload 'Mechatronics Project Parts_Data.xlsx'")
    st.stop()

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
    
    # Columns
    c_cat = get_col(df_components, ["Category"])
    c_status = get_col(df_components, ["Status"])
    c_brand = get_col(df_components, ["Mfg", "Manufacturer", "Brand"])
    c_sub1 = get_col(df_components, ["SubCategory"])
    c_sub2 = get_col(df_components, ["SubCategory2"])

    # Filters
    st.sidebar.header("🔍 Filters")
    df_filtered = df_components.copy()

    if c_status:
        opts = sorted(list(df_components[c_status].unique()))
        sel = st.sidebar.multiselect("Status", opts, default=opts)
        if sel: df_filtered = df_filtered[df_filtered[c_status].isin(sel)]
    if c_cat:
        opts = sorted(list(df_components[c_cat].unique()))
        sel = st.sidebar.multiselect("Category", opts, default=opts)
        if sel: df_filtered = df_filtered[df_filtered[c_cat].isin(sel)]

    # --- TITLE & SEARCH ---
    c_title, c_search = st.columns([1, 1])
    with c_title:
        st.markdown("## 🏭 Inventory Cockpit")
    with c_search:
        search_inv = st.text_input("Search", placeholder="Search Inventory...", label_visibility="collapsed")
        if search_inv:
            mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_inv, case=False)).any(axis=1)
            df_filtered = df_filtered[mask]

    # --- ROW 1: KPIs ---
    total = len(df_filtered)
    avail = df_filtered[c_status].str.contains("Available", case=False).sum() if c_status else 0
    pct = int((avail/total)*100) if total > 0 else 0
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Total Parts", total)
    with k2: kpi_card("Availability", f"{pct}%", "#16a34a" if pct > 50 else "#dc2626")
    with k3: kpi_card("Categories", df_filtered[c_cat].nunique() if c_cat else 0)
    with k4: kpi_card("Manufacturers", df_filtered[c_brand].nunique() if c_brand else 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ROW 2: STATUS & CATEGORY ---
    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        st.markdown('<div class="card-container"><div class="chart-title">Status Overview</div>', unsafe_allow_html=True)
        if c_status:
            stat_counts = df_filtered[c_status].value_counts().reset_index()
            stat_counts.columns = ["Status", "Count"]
            fig = px.pie(stat_counts, names="Status", values="Count", hole=0.6, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), showlegend=True, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="card-container"><div class="chart-title">Category Distribution</div>', unsafe_allow_html=True)
        if c_cat:
            cat_counts = df_filtered[c_cat].value_counts().reset_index().head(12)
            cat_counts.columns = ["Category", "Count"]
            fig = px.bar(cat_counts, x="Category", y="Count", text="Count", color="Count", color_continuous_scale="Blues")
            fig.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ROW 3: MANUFACTURERS (TREEMAP) ---
    st.markdown('<div class="card-container"><div class="chart-title">Top Manufacturers</div>', unsafe_allow_html=True)
    if c_brand:
        brand_data = df_filtered[c_brand].value_counts().reset_index().head(25)
        brand_data.columns = ["Brand", "Count"]
        
        fig = px.treemap(
            brand_data, 
            path=["Brand"], 
            values="Count", 
            color="Count", 
            color_continuous_scale="Mint",
            hover_data=["Count"]
        )
        fig.update_layout(height=350, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- ROW 4: EXPLORER (BOTTOM) ---
    st.markdown('<div class="card-container"><div class="chart-title">Data Explorer (Sunburst)</div>', unsafe_allow_html=True)
    if c_cat and c_sub1:
        df_sun = df_filtered.copy()
        df_sun[c_cat] = df_sun[c_cat].fillna("Unknown")
        df_sun[c_sub1] = df_sun[c_sub1].fillna("General")
        
        path = [c_cat, c_sub1]
        if c_sub2 and df_sun[c_sub2].notna().any():
            df_sun[c_sub2] = df_sun[c_sub2].fillna("-")
            path.append(c_sub2)
            
        fig = px.sunburst(df_sun, path=path, color=c_cat, color_discrete_sequence=px.colors.qualitative.Prism, maxdepth=3)
        fig.update_layout(height=600, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# DASHBOARD 2: DELIVERY (With HYBRID Search)
# ------------------------------------------------------------
elif page == "Delivery Tracking":
    
    s_set = get_col(df_sets, ["Set No", "Set"])
    s_status = get_col(df_sets, ["Final Status", "Status"])
    s_link = get_col(df_sets, ["Link", "Url"])
    
    if df_sets.empty or not s_set or not s_status:
        st.error("❌ Delivery Data Missing.")
        st.stop()
        
    st.markdown("## 🚚 Delivery Tracking")

    # --- 1. HYBRID SEARCH & FILTER ---
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        # A. SET SLICER (Dropdown) - Precise Selection
        all_sets = sorted(list(df_sets[s_set].unique()), key=natural_sort_key)
        selected_sets = st.multiselect("Select Set(s)", all_sets, placeholder="Choose specific sets (e.g. Set 1)")
    with f2:
        # B. TEXT SEARCH - Broad Search
        search_del = st.text_input("Text Search", placeholder="Type to find Part Name, Status, Link...", label_visibility="visible")

    # --- LOGIC: Combine Both Filters ---
    df_view = df_sets.copy()
    
    # Apply Set Filter if used
    if selected_sets:
        df_view = df_view[df_view[s_set].isin(selected_sets)]
    
    # Apply Text Search if used
    if search_del:
        mask = df_view.astype(str).apply(lambda x: x.str.contains(search_del, case=False)).any(axis=1)
        df_view = df_view[mask]
        
    st.caption(f"Showing {len(df_view)} items based on active filters.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 2. KPIs (Based on Filtered Data) ---
    total = len(df_view)
    released = df_view[s_status].str.contains("Released", case=False, na=False).sum()
    pending = total - released
    pct_rel = int((released/total)*100) if total > 0 else 0
    
    k1, k2, k3 = st.columns(3)
    with k1: kpi_card("Items in View", total)
    with k2: kpi_card("Released", released, "#16a34a")
    with k3: kpi_card("Pending", pending, "#dc2626")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. CHARTS ---
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown('<div class="card-container"><div class="chart-title">Readiness Gauge</div>', unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = pct_rel,
            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#3b82f6"}}
        ))
        fig_gauge.update_layout(height=250, margin=dict(t=20,b=20,l=25,r=25))
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card-container"><div class="chart-title">Set Composition</div>', unsafe_allow_html=True)
        if not df_view.empty:
            df_stack = df_view.groupby([s_set, s_status]).size().reset_index(name="Count")
            # Sort Graph Data
            df_stack = df_stack.sort_values(by=s_set, key=lambda col: col.map(lambda x: natural_sort_key(x)))
            
            colors = {"Released": "#22c55e", "Backorder": "#ef4444", "Split": "#eab308", "Out Of Stock": "#dc2626"}
            
            fig = px.bar(df_stack, x=s_set, y="Count", color=s_status, color_discrete_map=colors)
            fig.update_layout(height=280, margin=dict(t=10,b=0,l=0,r=0), legend=dict(orientation="h", y=1.1, title=None), xaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to chart.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. DETAILED LIST ---
    st.markdown('<div class="card-container"><div class="chart-title">⚠️ Exception Details</div>', unsafe_allow_html=True)
    
    # Filter Exceptions from CURRENT view
    df_exc = df_view[~df_view[s_status].str.contains("Released", case=False, na=False)]
    
    if not df_exc.empty:
        st.dataframe(
            df_exc[[s_set, s_status, s_link]],
            column_config={
                s_status: st.column_config.Column("Status", width="medium"),
                s_link: st.column_config.LinkColumn("Part Link"),
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
    else:
        if not df_view.empty:
            st.success("🎉 All items in this selection are Released!")
        else:
            st.info("No data selected.")
    st.markdown('</div>', unsafe_allow_html=True)