import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import json
import re

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
            special_list = sheet2.col_values(1)[1:] 
        except:
            special_list = []
        return df_fixed, special_list
    except Exception as e:
        st.error(f"❌ 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame(), []

# 🔥 부재 여부를 시간 기반으로 '엄격하게' 판별하는 함수
def is_currently_absent(schedule_str):
    # 현재 시간 (시, 분)
    now = datetime.datetime.now()
    now_val = now.hour * 100 + now.minute # 예: 18:30 -> 1830
    
    # '12-18' 또는 '12:00-18:00' 등 숫자 범위를 찾습니다.
    # 숫자만 달랑 있는 경우(12-18)를 위해 뒤에 00을 붙여서 비교합니다.
    time_match = re.search(r'(\d{1,2})[:]?(\d{0,2})[-~](\d{1,2})[:]?(\d{0,2})', schedule_str)
    
    if time_match:
        start_h = int(time_match.group(1))
        start_m = int(time_match.group(2)) if time_match.group(2) else 0
        end_h = int(time_match.group(3))
        end_m = int(time_match.group(4)) if time_match.group(4) else 0
        
        start_val = start_h * 100 + start_m
        end_val = end_h * 100 + end_m
        
        # 현재 시간이 범위 내에 있다면 '무조건' 부재 중
        if start_val <= now_val < end_val:
            return True
            
    # 시간 범위가 없거나 범위 밖이라면, 단어가 포함되어 있더라도 '활동 가능'으로 간주
    return False

df_fixed, special_list = get_las_data()

# 3. 메인 UI
if not df_fixed.empty:
    st.title("📅 lascheduler : 팀 실시간 시간표")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 데이터 즉시 동기화", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_btn2:
        st.link_button("📝 캘린더 시트 수정하러 가기", "https://docs.google.com/spreadsheets/d/139YrVpzvovwhOnyDDtHhYpYmL8etgJDw4NzKWQKET1o/edit?gid=0#gid=0", use_container_width=True)
    
    now = datetime.datetime.now()
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    today_name = days[now.weekday()]
    today_date = f"{now.month}/{now.day}"

    st.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M')} ({today_name})")

    st.subheader("👥 멤버 실시간 상태")
    for i, row in df_fixed.iterrows():
        if i % 3 == 0:
            cols = st.columns(3)
            
        with cols[i % 3]:
            name = str(row.get("이름", f"멤버{i+1}"))
            display_schedule = str(row.get(today_name, "자유"))
            is_special = False
            
            for note in special_list:
                if today_date in str(note) and name in str(note):
                    display_schedule = f"⭐ {note}"
                    is_special = True
                    break
            
            # 🔥 시간 기반 부재 중 판별 (단어보다 시간이 우선)
            absent_flag = is_currently_absent(display_schedule)
            
            if absent_flag:
                bg_color = "#ff8a80"  
                text_color = "#b71c1c" 
                status_text = "부재 중"
            else:
                bg_color = "#a5d6a7"  
                text_color = "#1b5e20" 
                status_text = "활동 가능"
                
            st.markdown(f"""
            <div style='display: flex; flex-direction: column; justify-content: center; align-items: center; border-radius: 12px; padding: 20px 10px; margin-bottom: 5px; background-color: {bg_color}; box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 110px;'>
                <div style='margin: 0; padding-bottom: 5px; font-size: 1.8rem; font-weight: bold; color: #111; text-align: center;'>{name}</div>
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
else:
    st.warning("데이터가 비어있거나 설정을 확인해 주세요!")
