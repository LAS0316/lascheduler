import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import re

st.set_page_config(page_title="lascheduler", layout="wide")

@st.cache_data(ttl=5)
def get_las_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
    client = gspread.authorize(creds)
    
    # 본인의 구글 시트 제목
    spreadsheet = client.open("펭별 시간표 공유") 
    
    # 1. 고정 일정 시트 읽기
    sheet1 = spreadsheet.worksheet("고정 일정")
    df_fixed = pd.DataFrame(sheet1.get_all_records())
    
    # 2. 특수 일정 시트 읽기
    try:
        sheet2 = spreadsheet.worksheet("특수 일정")
        # 데이터가 있는 모든 행을 리스트로 가져옴
        special_list = sheet2.col_values(1)[1:] # 첫 번째 열의 제목 제외 데이터들
    except:
        special_list = []
        
    return df_fixed, special_list

df_fixed, special_list = get_las_data()

if st.button("🔄 데이터 즉시 동기화"):
    st.cache_data.clear()
    st.rerun()

if not df_fixed.empty:
    st.title("📅 lascheduler : 팀 실시간 시간표")
    
    now = datetime.datetime.now()
    today_name = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()]
    today_date = f"{now.month}/{now.day}" # '3/4' 형태

    st.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M')} ({today_name})")

    cols = st.columns(len(df_fixed))
    
    for i, row in df_fixed.iterrows():
        with cols[i]:
            name = row.get("이름", f"멤버{i+1}")
            
            # 기본값은 고정 일정
            display_schedule = str(row.get(today_name, "자유"))
            is_special = False
            
            # 특수 일정 리스트에서 (오늘 날짜 + 이름)이 모두 포함된 문장이 있는지 검사
            for note in special_list:
                if today_date in note and name in note:
                    # 예: "라스 3/4 13-15 개인일정"에서 날짜와 이름을 뺀 나머지 내용 추출
                    display_schedule = f"⭐ {note}"
                    is_special = True
                    break # 가장 먼저 찾은 특수 일정 적용
            
            # 상태 판별 (수업, 알바, 개인일정)
            if any(kw in display_schedule for kw in ["수업", "알바", "개인일정"]):
                status_icon, status_text = "🔴", "부재 중"
            elif "자유" in display_schedule or not display_schedule.strip():
                status_icon, status_text = "🟢", "활동 가능"
            else:
                status_icon, status_text = "🟡", "확인 필요"
                
            st.metric(label=name, value=f"{status_icon} {status_text}")
            
            if is_special:
                st.warning(display_schedule)
            else:
                st.caption(f"일정: {display_schedule}")

    st.divider()
    st.subheader("🗓️ 주간 고정 일정표 (las-bot)")
    st.dataframe(df_fixed, use_container_width=True)
