import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import json
import re
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="lascheduler", layout="wide")

# 2. 데이터 로드 함수
@st.cache_data(ttl=5)
def get_las_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        key_dict = json.loads(st.secrets["gcp_service_account"]["json_data"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("펭별 시간표 공유") 
        
        sheet1 = spreadsheet.worksheet("고정 일정")
        df_fixed = pd.DataFrame(sheet1.get_all_records())
        
        try:
            sheet2 = spreadsheet.worksheet("특수 일정")
            # A열: 방송 일정, B열: 특수 일정 (2행 예시 제외)
            broadcast_list = sheet2.col_values(1)[2:] 
            special_list = sheet2.col_values(2)[2:] 
        except:
            broadcast_list, special_list = [], []
            
        return df_fixed, broadcast_list, special_list
    except Exception as e:
        st.error(f"❌ 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame(), [], []

# 한국 시간 기준 부재 판별 함수
def is_currently_absent(schedule_str):
    tz_kst = pytz.timezone('Asia/Seoul')
    now = datetime.datetime.now(tz_kst)
    now_val = now.hour * 100 + now.minute
    time_match = re.search(r'(\d{1,2})[:]?(\d{0,2})[-~](\d{1,2})[:]?(\d{0,2})', schedule_str)
    if time_match:
        start_h = int(time_match.group(1))
        start_m = int(time_match.group(2)) if time_match.group(2) else 0
        end_h = int(time_match.group(3))
        end_m = int(time_match.group(4)) if time_match.group(4) else 0
        if start_h * 100 + start_m <= now_val < end_h * 100 + end_m:
            return True
    return False

df_fixed, broadcast_list, special_list = get_las_data()

# 3. 메인 UI
if not df_fixed.empty:
    tz_kst = pytz.timezone('Asia/Seoul')
    now = datetime.datetime.now(tz_kst)
    today_date = f"{now.month:02d}/{now.day:02d}"
    
    # 상단 타이틀 변경
    st.title("📅 펭별 시간표")

    # 🔥 [수정] 간결해진 방송 공지 (이모지 및 TODAY LIVE 문구 제거)
    today_broadcasts = [b for b in broadcast_list if today_date in str(b)]
    if today_broadcasts:
        for b in today_broadcasts:
            st.error(f"오늘 방송: {b}")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 데이터 즉시 동기화", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_btn2:
        st.link_button("📝 캘린더 시트 수정하러 가기", "https://docs.google.com/spreadsheets/d/139YrVpzvovwhOnyDDtHhYpYmL8etgJDw4NzKWQKET1o/edit?gid=0#gid=0", use_container_width=True)
    
    st.subheader("👥 멤버 실시간 상태")
    for i, row in df_fixed.iterrows():
        if i % 3 == 0:
            cols = st.columns(3)
        with cols[i % 3]:
            name = str(row.get("이름", f"멤버{i+1}"))
            name_color = str(row.get("색코드", "#37474F")).strip() or "#37474F"
            
            days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
            today_name = days[now.weekday()]
            display_schedule = str(row.get(today_name, "자유"))
            is_special = False
            
            for note in special_list:
                if today_date in str(note) and name in str(note):
                    display_schedule = f"⭐ {note}"
                    is_special = True
                    break
            
            absent_flag = is_currently_absent(display_schedule)
            bg_color, text_color, status_text = ("#ff8a80", "#b71c1c", "부재 중") if absent_flag else ("#2ecc71", "#004d40", "활동 가능")
                
            st.markdown(f"""
            <div style='display: flex; flex-direction: column; justify-content: center; align-items: center; border-radius: 12px; padding: 20px 10px; margin-bottom: 5px; background-color: {bg_color}; box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 110px;'>
                <div style='margin: 0; padding-bottom: 5px; font-size: 1.8rem; font-weight: 900; color: {name_color}; text-align: center;'>{name}</div>
                <div style='font-size: 1.2rem; font-weight: 900; color: {text_color}; text-align: center;'>{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            caption_style = "text-align: center; margin-bottom: 15px;"
            if is_special:
                st.warning(f"<div style='{caption_style}'>{display_schedule}</div>", unsafe_allow_html=True)
            else:
                st.caption(f"<div style='{caption_style}'>일정: {display_schedule}</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🗓️ 주간 고정 일정표")
    st.dataframe(df_fixed, use_container_width=True)

    # 🔥 [수정] 한국 시간 정보를 가장 아래로 이동
    st.caption(f"최종 업데이트 확인 (KST): {now.strftime('%Y-%m-%d %H:%M')} ({today_name})")

else:
    st.warning("데이터가 비어있거나 설정을 확인해 주세요!")
