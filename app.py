import streamlit as st
from streamlit_gsheets import GSheetsConnection
import database as db
import utils
import views
import pandas as pd

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="@Dressmebesties.co Management System", layout="wide", initial_sidebar_state="expanded")

# โหลด CSS
try:
    utils.apply_custom_css()
except Exception as e:
    pass 

# ==========================================
# 1. ระบบรักษาความปลอดภัย (Login System)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #2563EB !important;'>@Dressmebesties.co</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #6B7280; margin-bottom: 20px;'>ระบบบริหารจัดการร้านเช่าชุด (Store Management System)</p>", unsafe_allow_html=True)
            
            pwd = st.text_input("รหัสผ่านร้าน (Password):", type="password", placeholder="กรุณากรอกรหัสผ่าน...")
            
            if st.button("เข้าสู่ระบบ (Login)", type="primary", use_container_width=True):
                if pwd.strip() == "1234":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("ข้อมูลไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
            
            st.write("")
            st.caption("ระบบได้รับการป้องกันความปลอดภัย กรุณาเก็บรักษารหัสผ่านเป็นความลับ")
            
    st.stop()

# ==========================================
# 2. ส่วนโปรแกรมหลัก (Main Application)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

if 'auto_cleaned' not in st.session_state:
    try:
        db.auto_clear_old_transactions(conn)
    except Exception as e: pass
    st.session_state['auto_cleaned'] = True

# --- โหลดข้อมูล Products ---
df_prod = db.get_products(conn)
if df_prod is None or df_prod.empty:
    df_prod = pd.DataFrame(columns=['id', 'name', 'category', 'size', 'color', 'price', 'price_1d', 'price_3d', 'price_5d', 'price_7d', 'price_15d', 'fine_per_day', 'status', 'image_url'])
else:
    # Migrate ข้อมูลราคาเดิมให้เป็นราคา 1 วัน อัตโนมัติ (ป้องกัน Error)
    if 'price' in df_prod.columns and 'price_1d' not in df_prod.columns:
        df_prod['price_1d'] = df_prod['price']
        
    expected_cols_prod = {
        'size': '-', 'color': '-', 'status': 'ว่าง', 'image_url': '',
        'price_1d': 0, 'price_3d': 0, 'price_5d': 0, 'price_7d': 0, 'price_15d': 0, 'price': 0
    }
    for col, default_val in expected_cols_prod.items():
        if col not in df_prod.columns:
            df_prod[col] = default_val

# --- โหลดข้อมูล Transactions ---
df_trans = db.get_transactions(conn)
if df_trans is None or df_trans.empty:
    df_trans = pd.DataFrame(columns=['date', 'prod_id', 'cus_name', 'cus_phone', 'address', 'action', 'status', 'start_date', 'end_date', 'total_price', 'note'])
else:
    if 'total_price' not in df_trans.columns:
        df_trans['total_price'] = 0

# --- โหลดข้อมูล Customers ---
df_cus = db.get_customers(conn)
if df_cus is None or df_cus.empty:
    df_cus = pd.DataFrame(columns=['name', 'phone', 'address', 'note'])
else:
    if 'note' not in df_cus.columns:
        df_cus['note'] = '-'

# --- แถบเมนูด้านซ้าย (Sidebar) ---
st.sidebar.title("👗 @Dressmebesties")
st.sidebar.caption("Store Management System")
st.sidebar.divider()

menu_options = [
    "ภาพรวมระบบ (Dashboard)", 
    "จัดการหน้าร้าน (POS)", 
    "ระบบคำสั่งซื้อ (Orders)", 
    "ตารางกำหนดการ (Calendar)", 
    "จัดการสินค้าส่งซัก (Laundry)", 
    "ฐานข้อมูลลูกค้า (Customers)", 
    "รายงานการเงิน (Finance)"
]
choice = st.sidebar.radio("เมนูหลัก", menu_options, label_visibility="collapsed")

st.sidebar.divider()
if st.sidebar.button("ออกจากระบบ (Logout)", use_container_width=True):
    st.session_state['logged_in'] = False
    st.session_state.clear() 
    st.rerun()

# --- ระบบเปลี่ยนหน้า (Router) ---
try:
    if choice == "ภาพรวมระบบ (Dashboard)": 
        views.render_dashboard(df_prod, df_cus, df_trans)
    elif choice == "จัดการหน้าร้าน (POS)": 
        views.render_pos(conn, df_prod, df_cus, df_trans)
    elif choice == "ระบบคำสั่งซื้อ (Orders)": 
        views.render_orders(conn, df_prod, df_trans)
    elif choice == "ตารางกำหนดการ (Calendar)": 
        views.render_calendar(df_prod, df_trans)
    elif choice == "จัดการสินค้าส่งซัก (Laundry)": 
        views.render_laundry(conn, df_prod)
    elif choice == "ฐานข้อมูลลูกค้า (Customers)": 
        views.render_customers(conn, df_cus)
    elif choice == "รายงานการเงิน (Finance)": 
        views.render_accounting(conn, df_trans, df_prod)
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดหน้า '{choice}': {str(e)}")

# เรียกใช้งาน Modal ใบเสร็จ
if 'show_receipt_data' in st.session_state:
    data = st.session_state['show_receipt_data']
    try:
        utils.display_receipt_modal(data['html'], data['img'], data['filename'])
    except Exception as e:
        st.error("เกิดข้อผิดพลาดในการสร้างหรือแสดงใบเสร็จ")