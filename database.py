import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def clean_phone(val):
    s = str(val).strip()
    if s.startswith("'"): s = s[1:]
    if s.lower() in ['nan', 'none', '']: return ''
    if s.endswith('.0'): s = s[:-2]
    
    s_check = s.replace("-", "").replace(" ", "")
    if len(s_check) in [8, 9] and not s_check.startswith('0') and s_check.isdigit():
        return '0' + s_check
    return s

def get_products(conn):
    try:
        df = conn.read(worksheet="Products", ttl="10m")
        return df
    except Exception as e:
        return pd.DataFrame(columns=['id', 'name', 'category', 'size', 'color', 'price_1d', 'price_3d', 'price_5d', 'price_7d', 'price_15d', 'fine_per_day', 'status', 'image_url'])

def get_transactions(conn):
    try:
        df = conn.read(worksheet="Transactions", ttl="10m")
        if not df.empty and 'cus_phone' in df.columns:
            df['cus_phone'] = df['cus_phone'].apply(clean_phone)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['date', 'prod_id', 'cus_name', 'cus_phone', 'address', 'action', 'status', 'start_date', 'end_date', 'total_price', 'note'])

def get_customers(conn):
    try:
        df = conn.read(worksheet="Customers", ttl="10m")
        if not df.empty and 'phone' in df.columns:
            df['phone'] = df['phone'].apply(clean_phone)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['name', 'phone', 'address', 'note'])

def update_product_status(conn, p_ids, new_status, only_if_current_is=None):
    df_prod = get_products(conn)
    if df_prod.empty: return
    
    updated = False
    for p_id in p_ids:
        if p_id in df_prod['id'].values:
            idx = df_prod.index[df_prod['id'] == p_id].tolist()[0]
            curr_status = str(df_prod.at[idx, 'status']).strip()
            if only_if_current_is is None or curr_status in only_if_current_is:
                df_prod.at[idx, 'status'] = new_status
                updated = True
    if updated:
        conn.update(worksheet="Products", data=df_prod)
        st.cache_data.clear()

def update_transaction_status(conn, p_ids, new_status, current_status_list=['เช่าอยู่', 'จองแล้ว']):
    df_trans = get_transactions(conn)
    if df_trans.empty: return
    updated = False
    for pid in p_ids:
        df_trans['status'] = df_trans['status'].astype(str).str.strip()
        mask = (df_trans['prod_id'] == pid) & (df_trans['status'].isin(current_status_list))
        if mask.any():
            df_trans.loc[mask, 'status'] = new_status
            updated = True
    if updated:
        conn.update(worksheet="Transactions", data=df_trans)
        st.cache_data.clear()

def cancel_transactions(conn, cancel_list):
    df_trans = get_transactions(conn)
    df_prod = get_products(conn)
    updated = False
    for item in cancel_list:
        date_val = item['date']
        pid_val = item['prod_id']
        mask = (df_trans['date'] == date_val) & (df_trans['prod_id'] == pid_val)
        if mask.any():
            trans_status = str(df_trans.loc[mask, 'status'].values[0]).strip()
            if trans_status in ['เช่าอยู่', 'จองแล้ว']:
                if pid_val in df_prod['id'].values:
                    idx = df_prod.index[df_prod['id'] == pid_val].tolist()[0]
                    df_prod.at[idx, 'status'] = 'ว่าง'
            df_trans.loc[mask, 'status'] = 'ยกเลิก'
            updated = True
    if updated:
        conn.update(worksheet="Products", data=df_prod)
        conn.update(worksheet="Transactions", data=df_trans)
        st.cache_data.clear()

def add_product(conn, df_prod, p_id, name, cat, p1, p3, p5, p7, p15, fine, size, color):
    if p_id in df_prod['id'].values: return False
    new_row = pd.DataFrame([{
        'id': p_id, 'name': name, 'category': cat, 'size': size, 'color': color, 
        'price_1d': p1, 'price_3d': p3, 'price_5d': p5, 'price_7d': p7, 'price_15d': p15,
        'price': p1, 'fine_per_day': fine, 'status': 'ว่าง', 'image_url': ''
    }])
    updated_df = pd.concat([df_prod, new_row], ignore_index=True)
    conn.update(worksheet="Products", data=updated_df)
    st.cache_data.clear()
    return True

def edit_product_full(conn, df_prod, df_trans, old_id, new_id, name, cat, p1, p3, p5, p7, p15, fine, size, color):
    if old_id in df_prod['id'].values:
        idx = df_prod.index[df_prod['id'] == old_id].tolist()[0]
        df_prod.at[idx, 'id'] = new_id
        df_prod.at[idx, 'name'] = name
        df_prod.at[idx, 'category'] = cat
        df_prod.at[idx, 'size'] = size
        df_prod.at[idx, 'color'] = color
        df_prod.at[idx, 'price_1d'] = p1
        df_prod.at[idx, 'price_3d'] = p3
        df_prod.at[idx, 'price_5d'] = p5
        df_prod.at[idx, 'price_7d'] = p7
        df_prod.at[idx, 'price_15d'] = p15
        df_prod.at[idx, 'price'] = p1 # เผื่อฟังก์ชันเก่าเรียกใช้
        df_prod.at[idx, 'fine_per_day'] = fine
        conn.update(worksheet="Products", data=df_prod)
        if old_id != new_id and not df_trans.empty:
            mask = df_trans['prod_id'] == old_id
            if mask.any():
                df_trans.loc[mask, 'prod_id'] = new_id
                conn.update(worksheet="Transactions", data=df_trans)
        st.cache_data.clear()
        return True
    return False

def check_availability(conn, p_id, start_dt_str, end_dt_str):
    df_trans = get_transactions(conn)
    if df_trans.empty: return True
    
    df_trans['status'] = df_trans['status'].astype(str).str.strip()
    active_trans = df_trans[(df_trans['prod_id'] == p_id) & (df_trans['status'].isin(['เช่าอยู่', 'จองแล้ว']))]
    if active_trans.empty: return True

    try:
        s_new = pd.to_datetime(start_dt_str, format="%d/%m/%Y %H:%M") - timedelta(days=1)
        e_new = pd.to_datetime(end_dt_str, format="%d/%m/%Y %H:%M") + timedelta(days=1)
    except:
        s_new = pd.to_datetime(start_dt_str, dayfirst=True) - timedelta(days=1)
        e_new = pd.to_datetime(end_dt_str, dayfirst=True) + timedelta(days=1)

    for _, row in active_trans.iterrows():
        try:
            s_exist = pd.to_datetime(row['start_date'], format="%d/%m/%Y %H:%M") - timedelta(days=1)
            e_exist = pd.to_datetime(row['end_date'], format="%d/%m/%Y %H:%M") + timedelta(days=1)
        except:
            s_exist = pd.to_datetime(row['start_date'], dayfirst=True) - timedelta(days=1)
            e_exist = pd.to_datetime(row['end_date'], dayfirst=True) + timedelta(days=1)
        
        if (s_new <= e_exist) and (e_new >= s_exist):
            return False 
    return True

def save_rental_transaction(conn, p_ids, c_name, c_phone, c_addr, start_str, end_str, total, note, action_status):
    df_trans = get_transactions(conn)
    now = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
    safe_phone = f"'{str(c_phone).strip()}" if str(c_phone).strip() else ""
    
    new_entries = []
    for pid in p_ids:
        new_entries.append({
            'date': now, 'prod_id': pid, 'cus_name': c_name, 'cus_phone': safe_phone,
            'address': c_addr, 'action': 'เช่า/จอง', 'status': action_status,
            'start_date': start_str, 'end_date': end_str, 'total_price': total, 'note': note
        })
    updated_trans = pd.concat([df_trans, pd.DataFrame(new_entries)], ignore_index=True)
    conn.update(worksheet="Transactions", data=updated_trans)
    
    if action_status == 'จองแล้ว':
        update_product_status(conn, p_ids, action_status, only_if_current_is=['ว่าง'])
    else:
        update_product_status(conn, p_ids, action_status)
        
    st.cache_data.clear()
    return now

def update_customer_db(conn, name, phone, addr, note):
    df_cus = get_customers(conn)
    safe_phone = f"'{str(phone).strip()}" if str(phone).strip() else ""
    
    if name in df_cus['name'].values:
        idx = df_cus.index[df_cus['name'] == name].tolist()[0]
        df_cus.at[idx, 'phone'] = safe_phone
        df_cus.at[idx, 'address'] = addr
        df_cus.at[idx, 'note'] = note
    else:
        new_cus = pd.DataFrame([{'name': name, 'phone': safe_phone, 'address': addr, 'note': note}])
        df_cus = pd.concat([df_cus, new_cus], ignore_index=True)
        
    conn.update(worksheet="Customers", data=df_cus)
    st.cache_data.clear()

def auto_clear_old_transactions(conn):
    df_trans = get_transactions(conn)
    if df_trans.empty or 'date' not in df_trans.columns: return
    temp_date = pd.to_datetime(df_trans['date'], errors='coerce')
    cutoff_date = datetime.utcnow() + timedelta(hours=7) - timedelta(days=1095)
    mask = temp_date >= cutoff_date
    if not mask.all():
        df_cleaned = df_trans[mask].copy()
        conn.update(worksheet="Transactions", data=df_cleaned)
        st.cache_data.clear()