import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import plotly.express as px
import calendar
import database as db
import utils
import re

# 🌟 หมวดหมู่สินค้าและรหัส Prefix
CAT_LIST = ["เสื้อ", "เสื้อคลุม", "ชุดเดรส", "กางเกง", "กระโปรง", "หมวก", "กระเป๋า", "เครื่องประดับ", "รองเท้า", "ชุดเซ็ท", "อื่นๆ"]
PREFIX_MAP = {
    "เสื้อ": "S-", "เสื้อคลุม": "C-", "ชุดเดรส": "D-", "กางเกง": "P-", "กระโปรง": "SK-",
    "หมวก": "H-", "กระเป๋า": "B-", "เครื่องประดับ": "A-", "รองเท้า": "SH-", "ชุดเซ็ท": "SET-", "อื่นๆ": "O-"
}
STATUS_LIST = ["ว่าง", "จองแล้ว", "เช่าอยู่", "รอซัก", "ไม่พร้อมใช้งาน", "สูญหาย", "ยกเลิกจำหน่าย"]
SIZE_LIST = ["XS", "S", "M", "L", "XL", "XXL", "Free Size", "อื่นๆ"]
COLOR_LIST = ["ขาว", "ดำ", "เทา", "แดง", "ชมพู", "ส้ม", "เหลือง", "เขียว", "ฟ้า", "น้ำเงิน", "ม่วง", "น้ำตาล", "อื่นๆ"]

def calc_rent_price(days, p1, p3, p5, p7, p15):
    try:
        d = max(1, int(days))
    except:
        d = 1
        
    def sf(val):
        try: return float(val)
        except: return 0.0
            
    p1, p3, p5, p7, p15 = sf(p1), sf(p3), sf(p5), sf(p7), sf(p15)
    
    total = 0
    if d >= 15 and p15 > 0:
        total += (d // 15) * p15; d = d % 15
    if d >= 7 and p7 > 0:
        total += (d // 7) * p7; d = d % 7
    if d >= 5 and p5 > 0:
        total += (d // 5) * p5; d = d % 5
    if d >= 3 and p3 > 0:
        total += (d // 3) * p3; d = d % 3
    if d >= 1 and p1 > 0:
        total += d * p1
    elif d > 0 and p1 == 0:
        if p3 > 0: total += d * (p3/3)
        elif p5 > 0: total += d * (p5/5)
        elif p7 > 0: total += d * (p7/7)
        elif p15 > 0: total += d * (p15/15)
        
    return total

def render_dashboard(df_prod, df_cus, df_trans):
    st.markdown("<h2 style='margin-bottom:0;'>รายงานภาพรวมระบบ (Dashboard)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:1.1rem; margin-top:0;'>แสดงข้อมูลสถิติ สถานะสินค้า และรายงานผลประกอบการ</p>", unsafe_allow_html=True)
    st.write("")
    
    active_prod = df_prod[df_prod['status'].astype(str).str.strip() != 'ยกเลิกจำหน่าย']
    total_items = len(active_prod)
    total_customers = len(df_cus)
    
    if not df_trans.empty:
        df_trans['status'] = df_trans['status'].astype(str).str.strip()
        valid_trans = df_trans[~df_trans['status'].isin(['รายจ่าย', 'ยกเลิก'])].copy()
        
        if not valid_trans.empty:
            valid_trans['date_dt'] = pd.to_datetime(valid_trans['date'], errors='coerce')
            grouped_valid = valid_trans.groupby('date').first().reset_index()
            grouped_valid['total_price'] = pd.to_numeric(grouped_valid['total_price'], errors='coerce').fillna(0)
            
            total_income = grouped_valid['total_price'].sum()
            total_orders = len(grouped_valid)
            
            daily_income = grouped_valid.groupby(grouped_valid['date_dt'].dt.date)['total_price'].sum().reset_index()
            daily_income.columns = ['date', 'income']
            daily_income = daily_income.sort_values('date', ascending=False).head(7)
        else:
            total_income, total_orders, daily_income = 0, 0, pd.DataFrame()
    else:
        total_income, total_orders, daily_income = 0, 0, pd.DataFrame()
        
    status_counts = active_prod['status'].astype(str).str.strip().value_counts()
    c_free = status_counts.get('ว่าง', 0)
    c_book = status_counts.get('จองแล้ว', 0)
    c_rent = status_counts.get('เช่าอยู่', 0)
    c_wash = status_counts.get('รอซัก', 0)

    c_t1, c_t2, c_t3 = st.columns(3)
    with c_t1:
        st.markdown(f"<div class='dash-top-card'><div class='dash-top-title'>จำนวนคำสั่งซื้อรวม (รายการ)</div><div class='dash-top-val'>{total_orders:,}</div></div>", unsafe_allow_html=True)
    with c_t2:
        st.markdown(f"<div class='dash-top-card'><div class='dash-top-title'>จำนวนลูกค้า (ราย)</div><div class='dash-top-val'>{total_customers:,}</div></div>", unsafe_allow_html=True)
    with c_t3:
        st.markdown(f"<div class='dash-top-card'><div class='dash-top-title'>สินค้าในระบบทั้งหมด (รายการ)</div><div class='dash-top-val'>{total_items:,}</div></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="dash-card-dark">
        <div class="dash-title-dark">ยอดรายได้สะสมสุทธิ (THB)</div>
        <div class="dash-val-white">฿ {total_income:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h4 style='color:#374151; font-size:1.1rem; margin-bottom:10px;'>สถานะคำสั่งซื้อและสินค้าปัจจุบัน</h4>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='dash-card-light card-free'><div class='dash-title'>พร้อมใช้งาน</div><div class='dash-value' style='color:#10B981;'>{c_free}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='dash-card-light card-book'><div class='dash-title'>ถูกจองล่วงหน้า</div><div class='dash-value' style='color:#3B82F6;'>{c_book}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='dash-card-light card-rent'><div class='dash-title'>อยู่ระหว่างใช้งาน</div><div class='dash-value' style='color:#EF4444;'>{c_rent}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='dash-card-light card-wash'><div class='dash-title'>รอทำความสะอาด</div><div class='dash-value' style='color:#F59E0B;'>{c_wash}</div></div>", unsafe_allow_html=True)
        
    st.write("")
    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#374151; font-size:1.1rem; margin-top:0;'>สัดส่วนสถานะสินค้าในระบบ</h4>", unsafe_allow_html=True)
        if not active_prod.empty and len(active_prod) > 0:
            df_status = status_counts.reset_index()
            df_status.columns = ['สถานะ', 'จำนวน']
            color_map = {'ว่าง': '#10B981', 'เช่าอยู่': '#EF4444', 'จองแล้ว': '#3B82F6', 'รอซัก': '#F59E0B', 'ไม่พร้อมใช้งาน': '#6B7280', 'สูญหาย': '#111827'}
            fig_pie = px.pie(df_status, values='จำนวน', names='สถานะ', hole=0.55, color='สถานะ', color_discrete_map=color_map)
            fig_pie.update_layout(template='plotly_white', margin=dict(t=10, b=10, l=0, r=0), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pie.update_traces(textposition='inside', textinfo='percent', textfont_size=14, marker=dict(line=dict(color='#FFFFFF', width=2)))
            st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_chart2:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#374151; font-size:1.1rem; margin-top:0;'>รายงานรายได้ประจำวัน (7 วันล่าสุด)</h4>", unsafe_allow_html=True)
        if not daily_income.empty:
            st.write("") 
            for _, row in daily_income.iterrows():
                dt_obj = pd.to_datetime(row['date'])
                day_name = dt_obj.strftime('%A')
                d_str = dt_obj.strftime('%d/%m/%Y')
                val = row['income']
                with st.container():
                    col_d1, col_d2 = st.columns([2, 1])
                    with col_d1:
                        st.markdown(f"<span style='color: #4B5563; font-size: 1rem; font-weight: 500;'>{day_name}, {d_str}</span>", unsafe_allow_html=True)
                    with col_d2:
                        st.markdown(f"<div style='text-align: right; color: #10B981; font-weight: 700; font-size: 1.1rem;'>+ ฿ {val:,.2f}</div>", unsafe_allow_html=True)
                    st.divider() 
        else:
            st.info("ยังไม่มีข้อมูลรายได้ในระบบ")
        st.markdown("</div>", unsafe_allow_html=True)

def render_pos(conn, df_prod, df_cus, df_trans):
    st.markdown("<h2 style='margin-bottom:0;'>จัดการหน้าร้าน (Point of Sale)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:1.1rem; margin-top:0;'>ระบบบันทึกรายการเช่า จอง รับคืน และจัดการฐานข้อมูลเบื้องต้น</p>", unsafe_allow_html=True)
    st.write("")
    action_mode = st.radio("กรุณาเลือกประเภทรายการ:", ["บันทึกการเช่า / จองสินค้า", "บันทึกการรับคืนสินค้า", "จัดการฐานข้อมูลสินค้า"], horizontal=True)
    st.write("---")

    if action_mode == "บันทึกการเช่า / จองสินค้า":
        st.markdown("##### 1. เลือกระยะเวลาการใช้งาน (เพื่อประเมินราคาแพ็กเกจ)")
        c_date, c_time, _ = st.columns([1.5, 1, 1.5])
        with c_date:
            dates = st.date_input("ระยะเวลาเช่า (ระบุวันรับ - วันคืน)", value=[], key="p_date", format="DD/MM/YYYY")
        with c_time:
            start_time = st.time_input("เวลาที่รับสินค้า", value=time(12, 0))
        
        num_days = 1
        start_dt_str = ""
        return_dt_str = ""
        if len(dates) == 2:
            num_days = (dates[1] - dates[0]).days + 1
            return_dt = datetime.combine(dates[0], start_time) + timedelta(days=num_days)
            start_dt_str = datetime.combine(dates[0], start_time).strftime("%d/%m/%Y %H:%M")
            return_dt_str = return_dt.strftime("%d/%m/%Y %H:%M")
            st.info(f"📌 ระยะเวลาใช้งานรวม: **{num_days} วัน** (กำหนดส่งคืน: {return_dt_str})")
        st.write("")
        
        col_l, col_r = st.columns([1.5, 1.2])
        with col_l:
            with st.container(border=True):
                st.subheader("2. เลือกรายการสินค้า")
                bookable_statuses = ['ว่าง', 'จองแล้ว', 'เช่าอยู่', 'รอซัก']
                df_free = df_prod[df_prod['status'].astype(str).str.strip().isin(bookable_statuses)].copy()
                if not df_free.empty:
                    df_free['cat_order'] = pd.Categorical(df_free['category'], categories=CAT_LIST, ordered=True)
                    df_free = df_free.sort_values(by=['cat_order', 'id']).drop(columns=['cat_order'])
                    
                    selected_options = st.multiselect(
                        "ค้นหารหัสสินค้า หรือ ชื่อสินค้า", 
                        df_free.apply(lambda r: f"{r['id']} - {r['name']} (หมวด: {r.get('category','-')}, ไซส์: {r.get('size', '-')}, สี: {r.get('color', '-')}) | {r.get('price_1d', r.get('price', 0))}฿/วัน", axis=1).tolist(), 
                        key="pos_sel"
                    )
                    p_ids = [s.split(" - ")[0] for s in selected_options]
                    if p_ids:
                        sel_items = df_prod[df_prod['id'].isin(p_ids)].copy()
                        sel_items['price'] = sel_items.apply(lambda x: calc_rent_price(
                            num_days, 
                            x.get('price_1d', x.get('price', 0)), 
                            x.get('price_3d', 0), 
                            x.get('price_5d', 0), 
                            x.get('price_7d', 0), 
                            x.get('price_15d', 0)
                        ), axis=1)
                        
                        base_total = sel_items['price'].sum()
                        
                        st.write("---")
                        st.markdown(f"<p style='color:#6B7280; font-size:0.9rem; margin-bottom:0;'>รวมค่าสินค้า (เช่า {num_days} วัน) - สามารถแก้ไขราคาเหมาได้</p>", unsafe_allow_html=True)
                        
                        edited_base_total = st.number_input("รวมค่าสินค้าทั้งหมด", min_value=0, value=int(base_total), step=50, key=f"price_{'-'.join(p_ids)}_days_{num_days}", label_visibility="collapsed")
                        
                        c_d1, c_d2 = st.columns(2)
                        with c_d1:
                            discount_pct = st.number_input("ส่วนลด (%)", min_value=0, max_value=100, value=0, step=5, key="disc_pct")
                        with c_d2:
                            shipping_fee = st.number_input("ค่าบริการจัดส่ง (บาท)", min_value=0, value=0, step=10, key="ship_fee")
                        
                        discount_amt = edited_base_total * (discount_pct / 100)
                        net_rent = edited_base_total - discount_amt
                        grand_total = net_rent + shipping_fee
                        
                        st.markdown(f"""
                        <div style='margin-top:15px; padding:15px; background-color:#F8FAFC; border-radius:8px; border:1px solid #E5E7EB;'>
                            <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                                <span style='color:#4B5563;'>รวมค่าสินค้า:</span>
                                <span style='font-weight:500;'>฿ {edited_base_total:,.2f}</span>
                            </div>
                            <div style='display:flex; justify-content:space-between; margin-bottom:8px; color:#EF4444;'>
                                <span>ส่วนลด ({discount_pct}%):</span>
                                <span style='font-weight:500;'>- ฿ {discount_amt:,.2f}</span>
                            </div>
                            <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                                <span style='color:#4B5563;'>ค่าจัดส่ง:</span>
                                <span style='font-weight:500;'>+ ฿ {shipping_fee:,.2f}</span>
                            </div>
                            <hr style='border:1px dashed #CBD5E1; margin:10px 0;'>
                            <div style='display:flex; justify-content:space-between; font-size:1.2rem;'>
                                <span style='color:#1E40AF; font-weight:600;'>ยอดชำระสุทธิ (Grand Total):</span>
                                <span style='color:#1D4ED8; font-weight:bold;'>฿ {grand_total:,.2f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("ไม่พบสินค้าที่สามารถทำรายการได้ในขณะนี้")
                
        with col_r:
            with st.container(border=True):
                st.subheader("3. ข้อมูลลูกค้าและการชำระเงิน")
                cus_list = df_cus['name'].tolist() if not df_cus.empty else []
                cus_choice = st.selectbox("เลือกข้อมูลลูกค้า", ["-- กรุณาเลือกลูกค้า --"] + cus_list, key="pos_cus")
                if cus_choice != "-- กรุณาเลือกลูกค้า --":
                    c_info = df_cus[df_cus['name'] == cus_choice].iloc[0]
                    st.markdown(f"<div style='background-color:#E5E7EB; padding:15px; border-radius:8px; margin-bottom:15px;'><b>{cus_choice}</b><br>เบอร์โทร: {c_info.get('phone', '')}<br>ที่อยู่: {c_info.get('address', '')}</div>", unsafe_allow_html=True)
                    
                    rent_type = st.radio("ประเภทการทำรายการ:", ["รับสินค้าทันที", "จองล่วงหน้า (ระบุวันรับสินค้า)"], horizontal=True)
                    note = st.text_input("รายละเอียดเพิ่มเติม / ค่ามัดจำ", placeholder="ระบุรายละเอียดเพิ่มเติม...", key="p_note")
                    st.write("")
                    
                    if st.button("บันทึกรายการและออกใบเสร็จ", key="p_btn", use_container_width=True):
                        if 'p_ids' in locals() and p_ids and len(dates) == 2:
                            overlap_items = [pid for pid in p_ids if not db.check_availability(conn, pid, start_dt_str, return_dt_str)]
                            if overlap_items:
                                st.error(f"ไม่สามารถทำรายการได้ สินค้ารหัส {', '.join(overlap_items)} ไม่พร้อมให้บริการในช่วงเวลาที่ระบุ")
                            else:
                                final_status = "เช่าอยู่" if "รับสินค้าทันที" in rent_type else "จองแล้ว"
                                
                                final_note = note.strip()
                                if discount_pct > 0: final_note = f"[ส่วนลด: {discount_pct}% (-{discount_amt:g} ฿)] {final_note}".strip()
                                if shipping_fee > 0: final_note = f"[ค่าจัดส่ง: {shipping_fee:g} ฿] {final_note}".strip()
                                if edited_base_total != base_total: final_note = f"[ราคาเหมา: {edited_base_total:g} ฿] {final_note}".strip()
                                
                                tx_time = db.save_rental_transaction(conn, p_ids, cus_choice, c_info.get('phone',''), c_info.get('address',''), start_dt_str, return_dt_str, grand_total, final_note, final_status)
                                display_tx_time = pd.to_datetime(tx_time).strftime("%d/%m/%Y %H:%M:%S")
                                
                                html_content, img_bytes = utils.create_receipt_assets(display_tx_time, cus_choice, c_info.get('phone',''), c_info.get('address',''), start_dt_str, return_dt_str, grand_total, final_note, final_status, sel_items, edited_base_total)
                                
                                st.session_state['show_receipt_data'] = {'html': html_content, 'img': img_bytes, 'filename': f"Receipt_{datetime.now().strftime('%Y%m%d%H%M')}.png"}
                                st.toast(f"บันทึกรายการเสร็จสิ้น (สถานะ: {final_status})")
                                st.rerun()
                        else:
                            st.error("กรุณาระบุข้อมูลสินค้าและระยะเวลาให้ครบถ้วน")

    elif action_mode == "บันทึกการรับคืนสินค้า":
        with st.container(border=True):
            st.subheader("บันทึกการรับคืนสินค้า")
            active_rent_trans = df_trans[df_trans['status'].astype(str).str.strip() == 'เช่าอยู่'] if not df_trans.empty else pd.DataFrame()
            
            if not active_rent_trans.empty:
                active_rent_trans['order_id'] = active_rent_trans['date'].apply(utils.generate_order_id)
                def make_ret_display(r):
                    p_info = df_prod[df_prod['id'] == r['prod_id']].iloc[0] if r['prod_id'] in df_prod['id'].values else {}
                    return f"[{r['order_id']}] {r['prod_id']} {p_info.get('name','')} - ลค. {r['cus_name']}"
                
                ret_options = active_rent_trans.apply(make_ret_display, axis=1).tolist()
                selected_ret = st.multiselect("ค้นหารหัสสินค้าเพื่อทำรายการรับคืน", ret_options, key="ret_sel")
                
                if selected_ret:
                    sel_order_ids = [s.split("]")[0].replace("[", "") for s in selected_ret]
                    sel_pids = [s.split("] ")[1].split(" ")[0] for s in selected_ret]
                    
                    total_late_fine = 0
                    for i in range(len(sel_pids)):
                        oid = sel_order_ids[i]
                        pid = sel_pids[i]
                        target_trans = active_rent_trans[(active_rent_trans['order_id'] == oid) & (active_rent_trans['prod_id'] == pid)].iloc[0]
                        p_inf = df_prod[df_prod['id'] == pid].iloc[0] if pid in df_prod['id'].values else {}
                        
                        try:
                            due_dt = pd.to_datetime(target_trans['end_date'], format="%d/%m/%Y %H:%M")
                        except:
                            due_dt = pd.to_datetime(target_trans['end_date'], dayfirst=True)
                        
                        allowed_due = due_dt + timedelta(days=1) 
                        if datetime.now() > allowed_due:
                            late_days = (datetime.now() - allowed_due).days + 1
                            fine = late_days * p_inf.get('fine_per_day', 0)
                            st.error(f"การแจ้งเตือนรหัส {pid}: ส่งคืนเกินกำหนด (กำหนดส่งคืน: {allowed_due.strftime('%d/%m/%Y %H:%M')}) (ค่าปรับ: {fine:,.2f} ฿)")
                            total_late_fine += fine
                        else:
                            st.success(f"รหัส {pid}: ส่งคืนภายในระยะเวลาที่กำหนด")
                            
                    st.write("---")
                    ret_condition = st.radio("สถานะสินค้าที่รับคืน:", ["ปกติ (ส่งทำความสะอาด)", "ชำรุด (ต้องการซ่อมแซม)", "สูญหาย (ตัดออกจากระบบ)"], horizontal=True)
                    damage_fine = 0
                    damage_note = ""
                    
                    if ret_condition != "ปกติ (ส่งทำความสะอาด)":
                        st.warning("หมายเหตุ: ระบบจะทำการระงับการให้บริการสินค้ารายการนี้โดยอัตโนมัติ")
                        c_f1, c_f2 = st.columns(2)
                        with c_f1:
                            damage_fine = st.number_input("ระบุค่าปรับชำรุด/สูญหาย (บาท)", min_value=0, value=0)
                        with c_f2:
                            damage_note = st.text_input("รายละเอียดเพิ่มเติม", placeholder="ระบุรายละเอียดความเสียหาย")
                            
                    st.write("")
                    if st.button("ยืนยันการรับคืนสินค้า", type="primary", use_container_width=True):
                        new_stat = "รอซัก" if "ปกติ" in ret_condition else ("ไม่พร้อมใช้งาน" if "ชำรุด" in ret_condition else "สูญหาย")
                        db.update_product_status(conn, sel_pids, new_stat)
                        db.update_transaction_status(conn, sel_pids, "คืนสินค้าแล้ว", current_status_list=['เช่าอยู่'])
                        
                        total_fine = total_late_fine + damage_fine
                        if total_fine > 0:
                            note_str = f"ค่าปรับล่าช้า {total_late_fine}฿ " if total_late_fine > 0 else ""
                            note_str += f"ค่าปรับชำรุด/สูญหาย {damage_fine}฿ ({damage_note})" if damage_fine > 0 else ""
                            cus_name = target_trans['cus_name']
                            db.save_rental_transaction(conn, ['-'], cus_name, '', '', '', '', total_fine, note_str.strip(), 'ค่าปรับ')
                            
                        st.success("บันทึกข้อมูลการรับคืนเสร็จสิ้น")
                        st.rerun()
            else:
                st.info("ไม่พบรายการสินค้าที่อยู่ระหว่างการเช่า")

    elif action_mode == "จัดการฐานข้อมูลสินค้า":
        st.subheader("ระบบจัดการฐานข้อมูลสินค้า")
        show_cols = ['id', 'name', 'category', 'size', 'color', 'fine_per_day', 'status', 'price_1d', 'price_3d', 'price_5d', 'price_7d', 'price_15d']
        display_df = df_prod[df_prod['status'].astype(str).str.strip() != 'ยกเลิกจำหน่าย'].copy()
        
        display_df['cat_order'] = pd.Categorical(display_df['category'], categories=CAT_LIST, ordered=True)
        display_df = display_df.sort_values(by=['cat_order', 'id']).drop(columns=['cat_order']).reset_index(drop=True)
        
        st.dataframe(display_df[[c for c in show_cols if c in display_df.columns]], use_container_width=True, hide_index=True)
        
        with st.expander("เพิ่ม / แก้ไข ข้อมูลสินค้า", expanded=True):
            # 🌟 เปลี่ยนจาก st.tabs เป็น st.radio เพื่อให้จำหน้าได้
            prod_mode = st.radio("โหมดจัดการสินค้า:", ["✨ เพิ่มรายการใหม่", "✏️ แก้ไข/ลบ ข้อมูลเดิม"], horizontal=True, key="prod_manage_mode", label_visibility="collapsed")
            st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            
            if prod_mode == "✨ เพิ่มรายการใหม่":
                col1, col2 = st.columns(2)
                with col1:
                    ncat = st.selectbox("หมวดหมู่สินค้า", CAT_LIST, key="a_cat")
                    prefix = PREFIX_MAP.get(ncat, "O-")
                    
                    existing_ids = df_prod[df_prod['id'].astype(str).str.startswith(prefix, na=False)]['id'].tolist()
                    max_num = 0
                    for eid in existing_ids:
                        num_part = str(eid).replace(prefix, "")
                        if num_part.isdigit():
                            max_num = max(max_num, int(num_part))
                    next_num_str = str(max_num + 1).zfill(3)
                    
                    nid_num = st.text_input(f"รหัสสินค้า (ส่วนต่อท้าย {prefix})", value=next_num_str, key=f"a_id_dyn_{prefix}")
                    nid = f"{prefix}{nid_num.strip()}" if nid_num else ""
                    nname = st.text_input("ชื่อสินค้า", key="a_name")
                with col2:
                    c_s, c_c = st.columns(2)
                    with c_s:
                        nsize = st.selectbox("ขนาด (Size)", SIZE_LIST, key="a_size")
                    with c_c:
                        c_color_sel = st.selectbox("สี", COLOR_LIST, key="a_color_sel")
                        ncolor = st.text_input("ระบุสี", key="a_color_custom") if c_color_sel == "อื่นๆ" else c_color_sel
                
                st.markdown("<div style='margin-top:10px; margin-bottom:5px; font-weight:600; color:#374151;'>ราคาค่าเช่าตามจำนวนวัน (บาท)</div>", unsafe_allow_html=True)
                c_p1, c_p3, c_p5 = st.columns(3)
                with c_p1:
                    n_p1 = st.number_input("ราคา 1 วัน", min_value=0, key="a_p1")
                with c_p3:
                    n_p3 = st.number_input("ราคา 3 วัน", min_value=0, key="a_p3")
                with c_p5:
                    n_p5 = st.number_input("ราคา 5 วัน", min_value=0, key="a_p5")
                    
                c_p7, c_p15, c_ef = st.columns(3)
                with c_p7:
                    n_p7 = st.number_input("ราคา 7 วัน", min_value=0, key="a_p7")
                with c_p15:
                    n_p15 = st.number_input("ราคา 15 วัน", min_value=0, key="a_p15")
                with c_ef:
                    nfine = st.number_input("อัตราค่าปรับ/วัน", min_value=0, key="a_fine")
                
                if st.button("บันทึกข้อมูลสินค้าใหม่", type="primary", key="save_new_btn", use_container_width=True):
                    if nid and nname: 
                        if db.add_product(conn, df_prod, nid, nname, ncat, n_p1, n_p3, n_p5, n_p7, n_p15, nfine, nsize, ncolor):
                            # 🌟 ล้างค่าหลังบันทึกสำเร็จ
                            keys_to_clear = ['a_cat', f'a_id_dyn_{prefix}', 'a_name', 'a_size', 'a_color_sel', 'a_color_custom', 'a_p1', 'a_p3', 'a_p5', 'a_p7', 'a_p15', 'a_fine']
                            for k in keys_to_clear:
                                if k in st.session_state: del st.session_state[k]
                            st.toast("เพิ่มข้อมูลสินค้าใหม่สำเร็จ! ✨")
                            st.rerun()
                        else:
                            st.error("รหัสสินค้านี้มีอยู่ในระบบแล้ว กรุณาใช้รหัสอื่น")
                    else:
                        st.warning("กรุณากรอกรหัสและชื่อสินค้าให้ครบถ้วน")
            
            else: # โหมดแก้ไข
                eid = st.selectbox("ค้นหารหัสเพื่อแก้ไขข้อมูล", [""] + display_df['id'].tolist(), key="e_sel")
                if eid:
                    curr = df_prod[df_prod['id'] == eid].iloc[0]
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        ecat = st.selectbox("หมวดหมู่สินค้า", CAT_LIST, index=CAT_LIST.index(curr['category']) if curr['category'] in CAT_LIST else 0, key="e_cat")
                        e_prefix = PREFIX_MAP.get(ecat, "O-")
                        curr_id_num = str(curr['id']).split("-")[-1] if "-" in str(curr['id']) else str(curr['id'])
                        eid_num = st.text_input(f"รหัสสินค้า (ส่วนต่อท้าย {e_prefix})", value=curr_id_num, key="e_id")
                        new_eid = f"{e_prefix}{eid_num.strip()}" if eid_num else curr['id']
                        ename = st.text_input("ชื่อสินค้า", value=curr['name'], key="e_name")
                        curr_status = str(curr['status']).strip()
                        estatus = st.selectbox("สถานะสินค้า", STATUS_LIST, index=STATUS_LIST.index(curr_status) if curr_status in STATUS_LIST else 0, key="e_status")
                    with col_e2:
                        e_s, e_c = st.columns(2)
                        with e_s:
                            curr_size = curr.get('size', 'Free Size')
                            esize = st.selectbox("ขนาด (Size)", SIZE_LIST, index=SIZE_LIST.index(curr_size) if curr_size in SIZE_LIST else len(SIZE_LIST)-1, key="e_size")
                        with e_c: 
                            curr_color = curr.get('color', 'ขาว')
                            idx_color = COLOR_LIST.index(curr_color) if curr_color in COLOR_LIST else len(COLOR_LIST) - 1
                            sel_ecolor = st.selectbox("สี", COLOR_LIST, index=idx_color, key="e_color_sel")
                            ecolor = st.text_input("ระบุสี", value=curr_color, key="e_color_custom") if sel_ecolor == "อื่นๆ" else sel_ecolor
                    
                    st.markdown("<div style='margin-top:10px; margin-bottom:5px; font-weight:600; color:#374151;'>ราคาค่าเช่าตามจำนวนวัน (บาท)</div>", unsafe_allow_html=True)
                    c_ep1, c_ep3, c_ep5 = st.columns(3)
                    with c_ep1:
                        e_p1 = st.number_input("ราคา 1 วัน", value=int(curr.get('price_1d', curr.get('price', 0))), key="e_p1")
                    with c_ep3:
                        e_p3 = st.number_input("ราคา 3 วัน", value=int(curr.get('price_3d', 0)), key="e_p3")
                    with c_ep5:
                        e_p5 = st.number_input("ราคา 5 วัน", value=int(curr.get('price_5d', 0)), key="e_p5")
                    
                    c_ep7, c_ep15, c_eef = st.columns(3)
                    with c_ep7:
                        e_p7 = st.number_input("ราคา 7 วัน", value=int(curr.get('price_7d', 0)), key="e_p7")
                    with c_ep15:
                        e_p15 = st.number_input("ราคา 15 วัน", value=int(curr.get('price_15d', 0)), key="e_p15")
                    with c_eef:
                        efine = st.number_input("อัตราค่าปรับ/วัน", value=int(curr.get('fine_per_day', 0)), key="e_fine")
                    
                    st.write("")
                    c_btn1, c_btn2 = st.columns([3, 1])
                    with c_btn1:
                        if st.button("อัปเดตข้อมูลสินค้า", type="primary", use_container_width=True):
                            if new_eid != eid and new_eid in df_prod['id'].values:
                                st.error("รหัสสินค้าใหม่นี้มีอยู่ในระบบแล้ว กรุณาใช้รหัสอื่น")
                            else:
                                if db.edit_product_full(conn, df_prod, df_trans, eid, new_eid, ename, ecat, e_p1, e_p3, e_p5, e_p7, e_p15, efine, esize, ecolor):
                                    db.update_product_status(conn, [new_eid], estatus)
                                    st.toast("อัปเดตข้อมูลสินค้าสำเร็จ! ✅")
                                    st.rerun()
                    with c_btn2:
                        if st.button("🗑️ ลบสินค้า", use_container_width=True):
                            db.update_product_status(conn, [eid], "ยกเลิกจำหน่าย")
                            st.toast(f"ลบสินค้ารหัส {eid} สำเร็จ (ซ่อนจากระบบโดยไม่กระทบบิลเก่า) 🗑️")
                            st.rerun()

def render_orders(conn, df_prod, df_trans):
    st.markdown("<h2 style='margin-bottom:0;'>ระบบจัดการคำสั่งซื้อ (Order Management)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:1.1rem; margin-top:0;'>ตรวจสอบและอัปเดตสถานะคำสั่งซื้อทั้งหมดของระบบ</p>", unsafe_allow_html=True)
    st.write("")

    if not df_trans.empty:
        df_trans['status'] = df_trans['status'].astype(str).str.strip()
        df_trans['date_dt'] = pd.to_datetime(df_trans['date'], errors='coerce')
        df_clean_trans = df_trans[df_trans['status'] != 'รายจ่าย'].dropna(subset=['date_dt']) 
        
        if not df_clean_trans.empty:
            orders = []
            unique_dates = df_clean_trans['date'].unique()
            for d in unique_dates:
                rows = df_clean_trans[df_clean_trans['date'] == d]
                dt_obj = rows.iloc[0]['date_dt']
                fmt_date = dt_obj.strftime('%d/%m/%Y %H:%M') if pd.notnull(dt_obj) else d
                
                note_str = str(rows.iloc[0]['note'])
                edited_base = None
                match_edited = re.search(r'\[ราคาเหมา:\s*([\d,]+(?:\.\d+)?)\s*(?:฿|THB)?\]', note_str)
                if match_edited:
                    edited_base = float(match_edited.group(1).replace(',', ''))
                
                orders.append({
                    'date': d, 'display_date': fmt_date, 'date_dt': rows.iloc[0]['date_dt'],
                    'cus_name': rows.iloc[0]['cus_name'], 'cus_phone': rows.iloc[0]['cus_phone'],
                    'total_price': pd.to_numeric(rows.iloc[0]['total_price'], errors='coerce'),
                    'status': str(rows.iloc[0]['status']).strip(),
                    'items': rows['prod_id'].tolist(),
                    'start_date': rows.iloc[0]['start_date'], 'end_date': rows.iloc[0]['end_date'],
                    'note': note_str,
                    'edited_base_total': edited_base
                })
            orders_df = pd.DataFrame(orders).sort_values('date_dt', ascending=False)
            orders_df['order_id'] = orders_df['date'].apply(utils.generate_order_id)

            c_filt, c_search, c_date = st.columns([2, 1.2, 1.3])
            with c_filt:
                filter_status = st.radio("กรองตามสถานะ:", ["ทั้งหมด", "จองล่วงหน้า", "อยู่ระหว่างเช่า", "เสร็จสิ้น", "ยกเลิก"], horizontal=True, label_visibility="collapsed")
            with c_search:
                search_oid = st.text_input("ค้นหาตามออเดอร์", placeholder="เช่น 1A2B3")
            with c_date:
                filter_date = st.date_input("📅 ค้นหาคิวตามวันที่ใช้งาน", value=None, format="DD/MM/YYYY")

            if filter_status == "จองล่วงหน้า": orders_df = orders_df[orders_df['status'] == 'จองแล้ว']
            elif filter_status == "อยู่ระหว่างเช่า": orders_df = orders_df[orders_df['status'] == 'เช่าอยู่']
            elif filter_status == "เสร็จสิ้น": orders_df = orders_df[orders_df['status'].isin(['คืนสินค้าแล้ว', 'คืนสินค้าแล้ว (ชำรุด)', 'สูญหาย', 'ค่าปรับ'])]
            elif filter_status == "ยกเลิก": orders_df = orders_df[orders_df['status'] == 'ยกเลิก']
            
            if search_oid:
                orders_df = orders_df[orders_df['order_id'].str.contains(search_oid.strip(), case=False)]

            if isinstance(filter_date, date):
                def match_date(s_str, e_str, tgt):
                    try:
                        s_dt = pd.to_datetime(s_str, format="%d/%m/%Y %H:%M").date()
                        e_dt = pd.to_datetime(e_str, format="%d/%m/%Y %H:%M").date()
                    except:
                        try:
                            s_dt = pd.to_datetime(s_str, dayfirst=True).date()
                            e_dt = pd.to_datetime(e_str, dayfirst=True).date()
                        except:
                            return False
                    return s_dt <= tgt <= e_dt
                
                orders_df = orders_df[orders_df.apply(lambda r: match_date(r['start_date'], r['end_date'], filter_date), axis=1)]

            st.write("")
            count = 0
            if orders_df.empty:
                st.info("ไม่พบรายการคำสั่งซื้อที่ค้นหา")
            else:
                if isinstance(filter_date, date):
                    st.success(f"📅 พบ {len(orders_df)} ออเดอร์ ที่มีคิวต้องจัดการในวันที่ {filter_date.strftime('%d/%m/%Y')}")
                
                for _, order in orders_df.iterrows():
                    count += 1
                    if count > 50: break 
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([2.5, 3, 2, 2.5])
                        order_id = order['order_id']
                        
                        c1.markdown(f'<div style="line-height:1.4;"><span style="color:#6B7280; font-size:0.85rem;">เวลาทำรายการ: {order["display_date"]} | <b style="color:#2563EB;">#{order_id}</b></span><br><b>{order["cus_name"]}</b><br><span style="color:#6B7280; font-size:0.9rem;">เบอร์ติดต่อ: {order["cus_phone"]}</span></div>', unsafe_allow_html=True)
                        
                        items_html_list = []
                        for pid in order['items']:
                            p_info = df_prod[df_prod['id'] == pid].iloc[0] if pid in df_prod['id'].values else {}
                            p_name = p_info.get('name', '')
                            items_html_list.append(f"• {pid} {p_name}".strip())
                        items_str = "<br>".join(items_html_list)

                        c2.markdown(f'<div style="line-height:1.4;"><span style="color:#6B7280; font-size:0.85rem;">รายการสินค้า ({len(order["items"])} ชิ้น)</span><br><div style="font-size:0.95rem; font-weight:500; margin-top:4px; margin-bottom:4px;">{items_str}</div><span style="color:#6B7280; font-size:0.85rem;">ระยะเวลา: {order["start_date"]} ถึง {order["end_date"]}</span></div>', unsafe_allow_html=True)
                        
                        status_class = "bg-returned"
                        if order['status'] == 'จองแล้ว': status_class = "bg-booking"
                        elif order['status'] == 'เช่าอยู่': status_class = "bg-renting"
                        elif order['status'] in ['ยกเลิก', 'คืนสินค้าแล้ว (ชำรุด)', 'สูญหาย', 'ไม่พร้อมใช้งาน']: status_class = "bg-canceled"
                        elif order['status'] == 'ค่าปรับ': status_class = "bg-fine"
                        
                        c3.markdown(f'<div style="line-height:1.4; text-align:center;"><span style="color:#2563EB; font-size:1.2rem; font-weight:700;">฿ {order["total_price"]:,.2f}</span><br><div style="margin-top:5px;"><span class="status-badge {status_class}">{order["status"]}</span></div></div>', unsafe_allow_html=True)
                        
                        with c4:
                            with st.expander("การจัดการ / พิมพ์ใบเสร็จ"):
                                if order['status'] == 'จองแล้ว':
                                    if st.button("ยืนยันการส่งมอบสินค้า", key=f"p_{order['date']}", use_container_width=True):
                                        db.update_product_status(conn, order['items'], "เช่าอยู่", only_if_current_is=['ว่าง', 'จองแล้ว'])
                                        db.update_transaction_status(conn, order['items'], "เช่าอยู่", current_status_list=['จองแล้ว'])
                                        st.rerun()
                                elif order['status'] == 'เช่าอยู่':
                                    if st.button("ยืนยันการรับคืนสินค้า (ปกติ)", key=f"r_{order['date']}", use_container_width=True):
                                        db.update_product_status(conn, order['items'], "รอซัก")
                                        db.update_transaction_status(conn, order['items'], "คืนสินค้าแล้ว", current_status_list=['เช่าอยู่'])
                                        st.rerun()
                                        
                                if order['status'] not in ['ยกเลิก', 'คืนสินค้าแล้ว', 'คืนสินค้าแล้ว (ชำรุด)', 'สูญหาย', 'ค่าปรับ']:
                                    if st.button("ยกเลิกคำสั่งซื้อ", key=f"c_{order['date']}", use_container_width=True):
                                        cancel_list = [{'date': order['date'], 'prod_id': pid} for pid in order['items']]
                                        db.cancel_transactions(conn, cancel_list)
                                        st.rerun()
                                        
                                if st.button("พิมพ์ใบเสร็จรับเงิน", key=f"v_{order['date']}", use_container_width=True):
                                    p_ids = order['items']
                                    sel_items = df_prod[df_prod['id'].isin(p_ids)].copy()
                                    missing_ids = [pid for pid in p_ids if pid not in sel_items['id'].tolist()]
                                    if missing_ids:
                                        missing_df = pd.DataFrame([{'id': pid, 'name': '(ไม่อยู่ในระบบสต็อก)'} for pid in missing_ids])
                                        sel_items = pd.concat([sel_items, missing_df], ignore_index=True)
                                        
                                    num_days = 1
                                    try:
                                        s_dt = pd.to_datetime(order['start_date'], format="%d/%m/%Y %H:%M").date()
                                        e_dt = pd.to_datetime(order['end_date'], format="%d/%m/%Y %H:%M").date()
                                        num_days = (e_dt - s_dt).days
                                        if num_days < 1: num_days = 1
                                    except: pass
                                    
                                    sel_items['price'] = sel_items.apply(lambda x: calc_rent_price(
                                        num_days, 
                                        x.get('price_1d', x.get('price', 0)), 
                                        x.get('price_3d', 0), 
                                        x.get('price_5d', 0), 
                                        x.get('price_7d', 0), 
                                        x.get('price_15d', 0)
                                    ), axis=1)
                                        
                                    html_content, img_bytes = utils.create_receipt_assets(order['display_date'], order['cus_name'], str(order['cus_phone']).strip(), '-', order['start_date'], order['end_date'], float(order['total_price']), order['note'], order['status'], sel_items, order['edited_base_total'])
                                    st.session_state['show_receipt_data'] = {'html': html_content, 'img': img_bytes, 'filename': f"Receipt_{order['date'].replace(':', '')}.png"}
                                    st.rerun()

def render_calendar(df_prod, df_trans):
    st.markdown("""
    <style>
    .cal-day { min-height: 120px; padding: 6px; background: #FFFFFF; position: relative; z-index: 1; }
    .cal-day:hover { z-index: 10; } 
    .cal-day.other-month { background: #F9FAFB; }
    .cal-day.today-cell { background: #EFF6FF !important; box-shadow: inset 0 0 0 2px #3B82F6; }
    .today-badge { background-color: #3B82F6; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.65rem; margin-left: 5px; vertical-align: text-bottom; font-weight: normal; }
    .cal-ribbon { position: relative; cursor: pointer; transition: filter 0.2s; height: 24px; display: flex; align-items: center; box-sizing: border-box; z-index: 2; margin-top: 3px; }
    .cal-ribbon:hover { filter: brightness(0.95); z-index: 20; } 
    .cal-tooltip { visibility: hidden; width: max-content; min-width: 180px; max-width: 250px; background-color: #1F2937 !important; text-align: left; border-radius: 8px; padding: 10px; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); margin-top: 5px; opacity: 0; transition: opacity 0.2s; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); font-weight: normal; white-space: normal; line-height: 1.4; z-index: 100; pointer-events: none; }
    .cal-tooltip::after { content: ""; position: absolute; bottom: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: transparent transparent #1F2937 transparent; }
    .cal-ribbon:hover .cal-tooltip { visibility: visible; opacity: 1; }
    
    /* 📱 [เพิ่มใหม่] เวทมนตร์บังคับไม่ให้ล้นจอในมือถือ/iPad */
    @media (max-width: 820px) {
        .cal-tooltip {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: 90vw !important; /* กว้าง 90% ของจอมือถือ */
            max-width: 320px !important;
            z-index: 999999 !important;
            margin-top: 0 !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
            border: 1px solid #4B5563 !important;
        }
        .cal-tooltip::after {
            display: none !important; /* ซ่อนลูกศรชี้ */
        }
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<h2 style='margin-bottom:0;'>ตารางกำหนดการ (Booking Calendar)</h2>", unsafe_allow_html=True)
    
    if 'cal_month' not in st.session_state:
        st.session_state.cal_month = date.today().month
        st.session_state.cal_year = date.today().year
        
    def ch_m(d):
        st.session_state.cal_month += d
        if st.session_state.cal_month > 12:
            st.session_state.cal_month = 1
            st.session_state.cal_year += 1
        elif st.session_state.cal_month < 1:
            st.session_state.cal_month = 12
            st.session_state.cal_year -= 1
            
    cp, cc, cn = st.columns([1, 2, 1])
    with cp:
        st.button("เดือนก่อนหน้า", on_click=ch_m, args=(-1,), use_container_width=True)
    with cc:
        st.markdown(f"<h3 style='text-align:center; color:#2563EB !important;'>{st.session_state.cal_month}/{st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with cn:
        st.button("เดือนถัดไป", on_click=ch_m, args=(1,), use_container_width=True)
    
    df_cal = pd.DataFrame()
    order_slots = {}
    slot_ends = {}
    
    if not df_trans.empty:
        df_cal = df_trans[df_trans['status'].isin(['เช่าอยู่', 'จองแล้ว', 'คืนสินค้าแล้ว', 'คืนสินค้าแล้ว (ชำรุด)'])].copy()
        df_cal['start_dt'] = pd.to_datetime(df_cal['start_date'], format="%d/%m/%Y %H:%M", errors='coerce').fillna(pd.to_datetime(df_cal['start_date'], dayfirst=True, errors='coerce'))
        df_cal['end_dt'] = pd.to_datetime(df_cal['end_date'], format="%d/%m/%Y %H:%M", errors='coerce').fillna(pd.to_datetime(df_cal['end_date'], dayfirst=True, errors='coerce'))
        df_cal['start_d'] = df_cal['start_dt'].dt.date
        df_cal['end_d'] = df_cal['end_dt'].dt.date
        df_cal['prep_d'] = df_cal['start_d'] - timedelta(days=1)
        df_cal['ret_d'] = df_cal['end_d'] + timedelta(days=1)
        df_cal = df_cal.sort_values(by=['start_dt', 'cus_name'])
        
        order_spans = []
        for tx_date, group in df_cal.groupby('date', sort=False):
            s_d = group.iloc[0]['start_d']
            e_d = group.iloc[0]['end_d']
            status = str(group.iloc[0]['status']).strip()
            p_d = s_d - timedelta(days=1)
            r_d = e_d + timedelta(days=1)
            
            act_s = p_d if ("คืน" not in status and status != 'เช่าอยู่') else s_d
            act_e = r_d
            
            order_spans.append({'date': tx_date, 'start': act_s, 'end': act_e})
            
        df_spans = pd.DataFrame(order_spans).sort_values(by=['start', 'date'])
        for _, row in df_spans.iterrows():
            slot = 0
            while slot in slot_ends and slot_ends[slot] >= row['start']:
                slot += 1
            order_slots[row['date']] = slot
            slot_ends[slot] = row['end']
            
    month_days = calendar.Calendar(firstweekday=6).monthdatescalendar(st.session_state.cal_year, st.session_state.cal_month)
    html = '<div style="display: grid; grid-template-columns: repeat(7, 1fr); background: #E5E7EB; gap: 1px; border: 1px solid #E5E7EB;">'
    for week in month_days:
        for day in week:
            is_today = (day == date.today())
            is_curr = (day.month == st.session_state.cal_month)
            html += f'<div class="cal-day {"today-cell" if is_today else ""} {"other-month" if not is_curr else ""}">'
            html += f'<div style="font-weight: 600;">{day.day}{" (วันนี้)" if is_today else ""}</div>'
            
            active_on_day = {}
            if not df_cal.empty:
                use_matches = df_cal[(df_cal['start_d'] <= day) & (df_cal['end_d'] >= day)]
                for tx_date, group in use_matches.groupby('date', sort=False):
                    active_on_day[order_slots[tx_date]] = ('main', tx_date, group)
                    
                prep = df_cal[df_cal['prep_d'] == day]
                for tx_date, group in prep.groupby('date', sort=False):
                    status = str(group.iloc[0]['status']).strip()
                    if "คืน" not in status and status != 'เช่าอยู่':
                        active_on_day[order_slots[tx_date]] = ('prep', tx_date, group)
                        
                ret = df_cal[df_cal['ret_d'] == day]
                for tx_date, group in ret.groupby('date', sort=False):
                    active_on_day[order_slots[tx_date]] = ('ret', tx_date, group)
                    
                if active_on_day:
                    max_slot = max(active_on_day.keys())
                    for s in range(max_slot + 1):
                        if s in active_on_day:
                            etype, tx_date, group = active_on_day[s]
                            cus_name = group.iloc[0]['cus_name']
                            order_id = utils.generate_order_id(tx_date)
                            status = str(group.iloc[0]['status']).strip()
                            
                            if etype == 'main':
                                group_start = group.iloc[0]['start_d']
                                group_end = group.iloc[0]['end_d']
                                items = []
                                for pid in group['prod_id']:
                                    name = df_prod[df_prod['id']==pid]['name'].iloc[0] if pid in df_prod['id'].values else ''
                                    items.append(f"- {pid} {name}")
                                    
                                if "คืนสินค้าแล้ว" in status:
                                    h_text, b_bg, b_bdr, b_txt, icon = "ส่งคืนสินค้าแล้ว", "#D1FAE5", "#10B981", "#065F46", "✅"
                                elif status == 'เช่าอยู่':
                                    h_text, b_bg, b_bdr, b_txt, icon = "เช่าอยู่", "#DBEAFE", "#3B82F6", "#1E40AF", "👗"
                                else:
                                    h_text, b_bg, b_bdr, b_txt, icon = "โปรดเตรียมสินค้าจัดส่ง", "#FEF3C7", "#F59E0B", "#92400E", "📦"
                                    
                                is_start = (day == group_start) or (day.weekday() == 6)
                                is_end = (day == group_end) or (day.weekday() == 5)

                                m_left = "-7px" if not is_start else "0"
                                m_right = "-7px" if not is_end else "0"
                                rad = "0"
                                if is_start and is_end: rad = "4px"
                                elif is_start: rad = "4px 0 0 4px"
                                elif is_end: rad = "0 4px 4px 0"
                                b_left = f"3px solid {b_bdr}" if is_start else "none"
                                p_left = "6px" if is_start else "8px"
                                
                                tooltip_html = f'''<div class="cal-tooltip"><div style="background-color:#374151; padding:4px 8px; border-radius:4px; margin-bottom:8px; text-align:center; border: 1px solid #4B5563;"><span style="color:#FBBF24 !important; font-size:1.05rem; font-weight:800; letter-spacing:0.5px;">Order #{order_id}</span></div><b style="color:{b_bdr} !important; font-size:0.9rem;">{icon} {h_text}</b><div style="color:#F9FAFB !important; margin-top:6px;"><b>👤 ลูกค้า:</b> {cus_name}</div><div style="color:#D1D5DB !important; font-size:0.8rem; margin-top:2px;">📞 โทร: {group.iloc[0]["cus_phone"]}</div><hr style="border:0; border-top:1px dashed #4B5563; margin:8px 0;"><div style="color:#F9FAFB !important; line-height:1.4;"><b style="font-size:0.8rem; color:#9CA3AF !important;">รายการชุด ({len(group)} ชิ้น):</b><br>{"<br>".join(items)}</div></div>'''

                                if is_start:
                                    inner = f'<div style="font-weight:600; font-size:0.7rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%; padding-top:2px; padding-bottom:2px;">{icon} {cus_name}</div>'
                                else:
                                    inner = f'<div style="width:100%; height:100%; color:transparent; user-select:none;">-</div>'
                                html += f'<div class="cal-ribbon" style="background:{b_bg}; border-left:{b_left}; color:{b_txt}; padding:0 {p_left}; margin-left:{m_left}; margin-right:{m_right}; border-radius:{rad};">{inner}{tooltip_html}</div>'
                                
                            elif etype == 'prep':
                                html += f'<div style="background:#FEE2E2; color:#991B1B; font-size:0.65rem; margin-top:3px; height:24px; padding:0 6px; border-radius:3px; border-left: 2px solid #EF4444; display:flex; align-items:center; box-sizing:border-box; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">📦 เตรียม [#{order_id}]: {cus_name}</div>'
                                
                            elif etype == 'ret':
                                if "คืน" in status:
                                    html += f'<div style="background:#D1FAE5; color:#065F46; font-size:0.65rem; margin-top:3px; height:24px; padding:0 6px; border-radius:3px; border-left: 2px solid #10B981; display:flex; align-items:center; box-sizing:border-box; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">✅ ส่งคืนแล้ว [#{order_id}]: {cus_name}</div>'
                                else:
                                    html += f'<div style="background:#FEF3C7; color:#92400E; font-size:0.65rem; margin-top:3px; height:24px; padding:0 6px; border-radius:3px; border-left: 2px solid #F59E0B; display:flex; align-items:center; box-sizing:border-box; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">📥 รอรับคืน [#{order_id}]: {cus_name}</div>'
                        else:
                            html += '<div style="height: 24px; margin-top: 3px; width: 100%;"></div>'
            html += '</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    st.caption("✨ เอาเมาส์ชี้ (Hover) ที่แถบออเดอร์เพื่อดูรายละเอียดรายการชุดและเบอร์โทรศัพท์ของลูกค้า")

def render_laundry(conn, df_prod):
    st.markdown("<h2 style='margin-bottom:0;'>ระบบจัดการสินค้าส่งซัก (Laundry Management)</h2>", unsafe_allow_html=True)
    st.write("")
    with st.container(border=True):
        st.subheader("อัปเดตสถานะสินค้าหลังทำความสะอาด")
        df_wash = df_prod[df_prod['status'].astype(str).str.strip() == 'รอซัก'] if not df_prod.empty else pd.DataFrame()
        if not df_wash.empty:
            wash_options = df_wash.apply(lambda r: f"{r['id']} - {r['name']} (สี: {r.get('color', '-')}, ไซส์: {r.get('size', '-')})", axis=1).tolist()
            selected_wash = st.multiselect("เลือกรายการสินค้าที่ทำความสะอาดเสร็จสิ้น (ปรับสถานะเป็น 'พร้อมใช้งาน')", wash_options, key="w_sel")
            to_wash = [s.split(" - ")[0] for s in selected_wash]
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("ยืนยันรายการที่เลือก", type="primary", use_container_width=True):
                    if to_wash:
                        db.update_product_status(conn, to_wash, "ว่าง")
                        st.success("อัปเดตสถานะสินค้าเสร็จสิ้น")
                        st.rerun()
                    else:
                        st.warning("กรุณาเลือกรายการสินค้าเพื่อดำเนินการ")
            with c_btn2:
                if st.button("ยืนยันสินค้าทั้งหมดพร้อมใช้งาน", use_container_width=True):
                    all_wash_ids = df_wash['id'].tolist()
                    db.update_product_status(conn, all_wash_ids, "ว่าง")
                    st.success("อัปเดตสถานะสินค้าทั้งหมดเสร็จสิ้น")
                    st.rerun()
        else:
            st.info("ไม่มีรายการสินค้าที่รอดำเนินการซัก")

def render_customers(conn, df_cus):
    st.markdown("<h2 style='margin-bottom:0;'>ระบบจัดการฐานข้อมูลลูกค้า (Customers)</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B7280; font-size:1.1rem; margin-top:0;'>บริหารจัดการข้อมูลลูกค้าสำหรับการทำรายการ</p>", unsafe_allow_html=True)
    st.write("")
    with st.expander("เพิ่ม / แก้ไข ข้อมูลลูกค้า", expanded=True):
        # 🌟 เปลี่ยน Tabs เป็น Radio เพื่อให้จำหน้าได้
        cus_mode = st.radio("โหมดจัดการลูกค้า:", ["✨ เพิ่มรายการใหม่", "✏️ แก้ไขข้อมูลเดิม"], horizontal=True, key="cus_manage_mode", label_visibility="collapsed")
        st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        
        if cus_mode == "✨ เพิ่มรายการใหม่":
            col1, col2 = st.columns(2)
            with col1:
                nc_name = st.text_input("ชื่อ-นามสกุล", key="c_name")
                nc_phone = st.text_input("เบอร์ติดต่อ", key="c_phone")
            with col2:
                nc_addr = st.text_area("ที่อยู่", key="c_addr", height=110)
                
            if st.button("บันทึกข้อมูลลูกค้า", type="primary", use_container_width=True):
                if nc_name:
                    db.update_customer_db(conn, nc_name, nc_phone, nc_addr, "")
                    # 🌟 ล้างค่าหลังบันทึกสำเร็จ
                    for k in ['c_name', 'c_phone', 'c_addr']:
                        if k in st.session_state: del st.session_state[k]
                    st.toast("บันทึกข้อมูลสำเร็จ! ✅")
                    st.rerun()
                else:
                    st.error("กรุณาระบุชื่อ-นามสกุล")
        else: # โหมดแก้ไข
            c_names = df_cus['name'].tolist() if not df_cus.empty else []
            sel_cus = st.selectbox("ค้นหาข้อมูลลูกค้าเพื่อแก้ไข", [""] + c_names, key="e_cus_sel")
            if sel_cus:
                curr_cus = df_cus[df_cus['name'] == sel_cus].iloc[0]
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.text_input("ชื่อ-นามสกุล (ไม่สามารถแก้ไขได้เพื่อป้องกันความผิดพลาดในใบสั่งซื้อเดิม)", value=curr_cus['name'], disabled=True, key="ec_name_disabled")
                    ec_phone = st.text_input("เบอร์ติดต่อ", value=curr_cus.get('phone', ''), key="ec_phone")
                with col_e2:
                    ec_addr = st.text_area("ที่อยู่", value=curr_cus.get('address', ''), key="ec_addr", height=110)
                    
                if st.button("อัปเดตข้อมูลลูกค้า", type="primary", key="ec_btn", use_container_width=True):
                    db.update_customer_db(conn, sel_cus, ec_phone, ec_addr, "")
                    st.toast("อัปเดตข้อมูลสำเร็จ! ✅")
                    st.rerun()
                    
    st.write("---")
    st.subheader("รายชื่อลูกค้าทั้งหมดในระบบ")
    st.dataframe(df_cus, use_container_width=True, hide_index=True)

def extract_shipping(note_text):
    match = re.search(r'\[ค่าจัดส่ง:\s*([\d,]+(?:\.\d+)?)\s*(?:฿|THB)?\]', str(note_text))
    if match: return float(match.group(1).replace(',', ''))
    return 0.0

def render_accounting(conn, df_trans, df_prod):
    st.markdown("<h2 style='margin-bottom:0;'>รายงานการเงินและบัญชี (Financial Report)</h2>", unsafe_allow_html=True)
    st.write("")
    
    if not df_trans.empty:
        df_trans['date_dt'] = pd.to_datetime(df_trans['date'], errors='coerce')
        df_trans['status'] = df_trans['status'].astype(str).str.strip()
        
        df_sales_raw = df_trans[df_trans['status'] != 'รายจ่าย'].copy()
        df_exp_raw = df_trans[df_trans['status'] == 'รายจ่าย'].copy()
        
        grouped_sales = []
        if not df_sales_raw.empty:
            for d, group in df_sales_raw.groupby('date'):
                first_row = group.iloc[0]
                status = str(first_row['status'])
                price = float(first_row['total_price']) if pd.notna(first_row['total_price']) else 0.0
                note_str = str(first_row['note'])
                
                ship_fee = 0.0
                if status == 'ยกเลิก':
                    price = 0.0 
                else:
                    ship_fee = extract_shipping(note_str)
                
                product_net = price - ship_fee if price >= ship_fee else 0.0
                
                prod_names = []
                for pid in group['prod_id']:
                    p_name_match = df_prod[df_prod['id'] == pid]['name'] if 'name' in df_prod.columns else None
                    p_name = p_name_match.iloc[0] if p_name_match is not None and not p_name_match.empty else ""
                    prod_names.append(f"{pid} {p_name}".strip())
                prod_display = ", ".join(prod_names)

                grouped_sales.append({
                    'date': d,
                    'date_dt': first_row['date_dt'],
                    'cus_name': first_row['cus_name'],
                    'prod_id_name': prod_display,
                    'product_net': product_net,
                    'shipping_fee': ship_fee,
                    'total_price': price,
                    'status': status,
                    'note': note_str
                })
        
        df_sales = pd.DataFrame(grouped_sales) if grouped_sales else pd.DataFrame(columns=['date', 'date_dt', 'cus_name', 'prod_id_name', 'product_net', 'shipping_fee', 'total_price', 'status', 'note'])
        
        total_revenue = df_sales['total_price'].sum() if not df_sales.empty else 0
        total_shipping = df_sales['shipping_fee'].sum() if not df_sales.empty else 0
        total_orders = len(df_sales[df_sales['status'] != 'ยกเลิก']) if not df_sales.empty else 0
        total_expense = pd.to_numeric(df_exp_raw['total_price'], errors='coerce').fillna(0).sum() if not df_exp_raw.empty else 0
        net_profit = total_revenue - total_expense

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"<div class='metric-card' style='border-top: 4px solid #3B82F6; padding:15px;'><div class='dash-title'>รายได้สะสมรวม</div><div class='dash-value' style='color:#3B82F6; font-size:1.6rem;'>฿{total_revenue:,.2f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card' style='border-top: 4px solid #8B5CF6; padding:15px;'><div class='dash-title'>รายได้ค่าจัดส่ง</div><div class='dash-value' style='color:#8B5CF6; font-size:1.6rem;'>฿{total_shipping:,.2f}</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-card' style='border-top: 4px solid #EF4444; padding:15px;'><div class='dash-title'>ค่าใช้จ่ายสะสม</div><div class='dash-value' style='color:#EF4444; font-size:1.6rem;'>฿{total_expense:,.2f}</div></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='metric-profit' style='padding:15px;'><div class='dash-title-dark' style='color:#A7F3D0 !important; font-size:0.9rem;'>กำไรสุทธิสะสม</div><div class='dash-val-white' style='font-size:1.8rem; color:#A7F3D0 !important;'>฿{net_profit:,.2f}</div></div>", unsafe_allow_html=True)
        with c5:
            st.markdown(f"<div class='metric-card' style='border-top: 4px solid #10B981; padding:15px;'><div class='dash-title'>จำนวนคำสั่งซื้อ</div><div class='dash-value' style='color:#10B981; font-size:1.6rem;'>{total_orders:,} รายการ</div></div>", unsafe_allow_html=True)
            
        st.write("---")
        with st.expander("บันทึกรายการค่าใช้จ่าย"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_title = st.text_input("รายละเอียดรายการค่าใช้จ่าย", key="exp_title")
            with col_e2:
                e_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0, key="exp_amount")
            if st.button("บันทึกข้อมูล", type="primary", use_container_width=True):
                if e_title and e_amount > 0:
                    db.save_rental_transaction(conn, ['-'], 'รายจ่ายทั่วไป', '', '', '', '', e_amount, e_title, 'รายจ่าย')
                    # 🌟 ล้างค่าหลังบันทึกสำเร็จ
                    for k in ['exp_title', 'exp_amount']:
                        if k in st.session_state: del st.session_state[k]
                    st.toast("บันทึกรายการสำเร็จ! 💸")
                    st.rerun()
                else:
                    st.error("กรุณาระบุรายละเอียดและจำนวนเงินให้ครบถ้วน")
                        
        st.write("---")
        st.markdown("<h4 style='color:#374151; font-size:1.1rem;'>ข้อมูลบัญชีและรายงาน</h4>", unsafe_allow_html=True)
        
        if not df_sales.empty: df_sales['Month'] = df_sales['date_dt'].dt.strftime('%Y-%m')
        if not df_exp_raw.empty: df_exp_raw['Month'] = df_exp_raw['date_dt'].dt.strftime('%Y-%m')
        
        all_months = set()
        if not df_sales.empty: all_months.update(df_sales['Month'].dropna().unique())
        if not df_exp_raw.empty: all_months.update(df_exp_raw['Month'].dropna().unique())
        months = sorted(list(all_months), reverse=True)
        
        if months:
            report_mode = st.radio("เลือกรูปแบบรายงาน:", ["สรุปรายเดือน", "สรุปรายวัน"], horizontal=True)
            
            if report_mode == "สรุปรายเดือน":
                sel_month = st.selectbox("เลือกเดือนที่ต้องการแสดงข้อมูล", months, label_visibility="collapsed")
                df_m_sales = df_sales[df_sales['Month'] == sel_month].copy() if not df_sales.empty else pd.DataFrame()
                df_m_expense = df_exp_raw[df_exp_raw['Month'] == sel_month].copy() if not df_exp_raw.empty else pd.DataFrame()
                report_label = f"เดือน {sel_month}"
                file_suffix = sel_month
            else:
                sel_date = st.date_input("เลือกวันที่ที่ต้องการแสดงข้อมูล", value=date.today(), format="DD/MM/YYYY")
                df_m_sales = df_sales[df_sales['date_dt'].dt.date == sel_date].copy() if not df_sales.empty else pd.DataFrame()
                df_m_expense = df_exp_raw[df_exp_raw['date_dt'].dt.date == sel_date].copy() if not df_exp_raw.empty else pd.DataFrame()
                report_label = f"วันที่ {sel_date.strftime('%d/%m/%Y')}"
                file_suffix = sel_date.strftime('%Y-%m-%d')
                
            sub_rev = df_m_sales['total_price'].sum() if not df_m_sales.empty else 0.0
            sub_exp = pd.to_numeric(df_m_expense['total_price'], errors='coerce').fillna(0).sum() if not df_m_expense.empty else 0.0
            sub_orders = len(df_m_sales[df_m_sales['status'] != 'ยกเลิก']) if not df_m_sales.empty else 0
            
            st.info(f"📊 **สรุปยอด {report_label}:** รายรับ **฿{sub_rev:,.2f}** | รายจ่าย **฿{sub_exp:,.2f}** | กำไรสุทธิ **฿{sub_rev - sub_exp:,.2f}** | คำสั่งซื้อ **{sub_orders}** รายการ")
            
            csv_data = []
            month_prod_net = 0.0
            month_ship = 0.0
            month_rev = 0.0
            
            if not df_m_sales.empty:
                for _, row in df_m_sales.sort_values('date_dt', ascending=False).iterrows():
                    order_no = f"#{utils.generate_order_id(row['date'])}"
                    csv_data.append({
                        'วันที่ทำรายการ': row['date_dt'].strftime('%d/%m/%Y %H:%M') if pd.notnull(row['date_dt']) else row['date'],
                        'เลขที่รายการ': order_no,
                        'ชื่อลูกค้า': row['cus_name'],
                        'รหัสสินค้าและชื่อสินค้า': row['prod_id_name'],
                        'ยอดสินค้า (THB)': row['product_net'],
                        'ค่าจัดส่ง (THB)': row['shipping_fee'],
                        'ยอดชำระรวม (THB)': row['total_price'],
                        'สถานะปัจจุบัน': row['status']
                    })
                    month_prod_net += row['product_net']
                    month_ship += row['shipping_fee']
                    month_rev += row['total_price']
            
            month_exp = 0.0
            if not df_m_expense.empty:
                for _, row in df_m_expense.sort_values('date_dt', ascending=False).iterrows():
                    order_no = f"#{utils.generate_order_id(row['date'])}"
                    price = float(row['total_price']) if pd.notna(row['total_price']) else 0.0
                    csv_data.append({
                        'วันที่ทำรายการ': row['date_dt'].strftime('%d/%m/%Y %H:%M') if pd.notnull(row['date_dt']) else row['date'],
                        'เลขที่รายการ': order_no,
                        'ชื่อลูกค้า': '-',
                        'รหัสสินค้าและชื่อสินค้า': f"[รายจ่าย] {str(row['note'])}",
                        'ยอดสินค้า (THB)': 0.0,
                        'ค่าจัดส่ง (THB)': 0.0,
                        'ยอดชำระรวม (THB)': price,
                        'สถานะปัจจุบัน': 'รายจ่าย'
                    })
                    month_exp += price
                    
            df_csv = pd.DataFrame(csv_data)
            month_net = month_rev - month_exp
            
            summary_rows = pd.DataFrame([
                {'วันที่ทำรายการ': '', 'เลขที่รายการ': '', 'ชื่อลูกค้า': '', 'รหัสสินค้าและชื่อสินค้า': '', 'ยอดสินค้า (THB)': None, 'ค่าจัดส่ง (THB)': None, 'ยอดชำระรวม (THB)': None, 'สถานะปัจจุบัน': ''},
                {'วันที่ทำรายการ': '', 'เลขที่รายการ': '', 'ชื่อลูกค้า': '', 'รหัสสินค้าและชื่อสินค้า': 'รวมรายได้ (Total Income)', 'ยอดสินค้า (THB)': month_prod_net, 'ค่าจัดส่ง (THB)': month_ship, 'ยอดชำระรวม (THB)': month_rev, 'สถานะปัจจุบัน': ''},
                {'วันที่ทำรายการ': '', 'เลขที่รายการ': '', 'ชื่อลูกค้า': '', 'รหัสสินค้าและชื่อสินค้า': 'รวมรายจ่าย (Total Expense)', 'ยอดสินค้า (THB)': 0.0, 'ค่าจัดส่ง (THB)': 0.0, 'ยอดชำระรวม (THB)': month_exp, 'สถานะปัจจุบัน': ''},
                {'วันที่ทำรายการ': '', 'เลขที่รายการ': '', 'ชื่อลูกค้า': '', 'รหัสสินค้าและชื่อสินค้า': 'กำไรสุทธิ (Net Profit)', 'ยอดสินค้า (THB)': None, 'ค่าจัดส่ง (THB)': None, 'ยอดชำระรวม (THB)': month_net, 'สถานะปัจจุบัน': ''}
            ])
            if not df_csv.empty:
                df_csv = pd.concat([df_csv, summary_rows], ignore_index=True)
            else:
                df_csv = summary_rows
            
            csv = df_csv.to_csv(index=False).encode('utf-8-sig') 
            st.download_button(label=f"ดาวน์โหลดรายงาน {report_label} (.csv)", data=csv, file_name=f"Financial_Report_{file_suffix}.csv", mime="text/csv", use_container_width=True)

            tab1, tab2 = st.tabs([f"รายรับ {report_label}", f"รายจ่าย {report_label}"])
            with tab1:
                if not df_m_sales.empty:
                    show_sales = df_m_sales[['date_dt', 'date', 'cus_name', 'prod_id_name', 'product_net', 'shipping_fee', 'total_price', 'status']].sort_values(by='date_dt', ascending=False)
                    show_sales['Order No.'] = show_sales['date'].apply(lambda x: f"#{utils.generate_order_id(x)}")
                    show_sales['date'] = show_sales['date_dt'].dt.strftime('%d/%m/%Y %H:%M')
                    
                    show_sales = show_sales[['date', 'Order No.', 'cus_name', 'prod_id_name', 'product_net', 'shipping_fee', 'total_price', 'status']]
                    show_sales.columns = ['วันที่ทำรายการ', 'เลขที่รายการ', 'ชื่อลูกค้า', 'รหัสสินค้าและชื่อสินค้า', 'ยอดสินค้า (THB)', 'ค่าจัดส่ง (THB)', 'ยอดชำระรวม (THB)', 'สถานะปัจจุบัน']
                    
                    st.dataframe(show_sales.style.format({'ยอดสินค้า (THB)': '{:,.2f}', 'ค่าจัดส่ง (THB)': '{:,.2f}', 'ยอดชำระรวม (THB)': '{:,.2f}'}), use_container_width=True, hide_index=True)
                else:
                    st.info(f"ไม่พบข้อมูลรายได้ใน {report_label}")
            with tab2:
                if not df_m_expense.empty:
                    show_exp = df_m_expense[['date_dt', 'date', 'note', 'total_price']].sort_values(by='date_dt', ascending=False)
                    show_exp['date'] = show_exp['date_dt'].dt.strftime('%d/%m/%Y %H:%M')
                    show_exp = show_exp[['date', 'note', 'total_price']]
                    show_exp.columns = ['วันที่ทำรายการ', 'รายละเอียดค่าใช้จ่าย', 'ยอดเงิน (THB)']
                    st.dataframe(show_exp.style.format({'ยอดเงิน (THB)': '{:,.2f}'}), use_container_width=True, hide_index=True)
                else:
                    st.info(f"ไม่พบข้อมูลรายจ่ายใน {report_label}")
        else:
            st.info("ระบบยังไม่มีข้อมูลสำหรับจัดทำรายงาน")
    else:
        st.info("ระบบยังไม่มีข้อมูลสำหรับจัดทำรายงาน")
