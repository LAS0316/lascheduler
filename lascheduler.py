import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import json

# --- lascheduler 페이지 설정 ---
st.set_page_config(page_title="lascheduler", layout="wide")

# --- las-bot 데이터 로드 함수 ---
@st.cache_data(ttl=5)
def get_las_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Streamlit Cloud의 Secrets에서 보안 정보 읽기
        # 설정창에 입력한 json_data 안의 내용을 딕셔너리로 변환합니다.
        key_dict = json.loads(st.secrets["gcp_service_account"]["json_data"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        
        # 구글 시트 이름: 펭별 시간표 공유
        spreadsheet = client.open("펭별 시간표 공유") 
        
        # 1. '고정 일정' 시트 데이터 읽기
        sheet1 = spreadsheet.worksheet("고정 일정")
        df_fixed = pd.DataFrame(sheet1.get_all_records())
        
        # 2. '특수 일정' 시트 데이터 읽기
        try:
            sheet2 = spreadsheet.worksheet("특수 일정")
            # 첫 번째 열의 모든 데이터를 가져옴 (제목 제외)
            special_list = sheet2.col_values(1)[1:] 
        except:
            special_list = []
            
        return df_fixed, special_list
        
    except Exception as e:
        st.error(f"❌ 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame(), []

# 데이터 불러오기
df_fixed, special_list = get_las_data()

# --- 화면 상단: 동기화 버튼 ---
if st.button("🔄 데이터 즉시 동기화"):
    st.cache_data.clear()
    st.rerun()

# --- 메인 대시보드 UI ---
if not df_fixed.empty:
    st.title("📅 lascheduler : 팀 실시간 시간표")
    
    now = datetime.datetime.now()
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    today_name = days[now.weekday()]
    today_date = f"{now.month}/{now.day}" # '3/4' 형태

    st.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M')} ({today_name})")

    st.subheader("👥 멤버 실시간 상태")
    cols = st.columns(len(df_fixed))
    
    for i, row in df_fixed.iterrows():
        with cols[i]:
            name = str(row.get("이름", f"멤버{i+1}"))
            
            # 기본 일정 (고정 일정 탭)
            display_schedule = str(row.get(today_name, "자유"))
            is_special = False
            
            # 특수 일정 체크 (오늘 날짜와 이름이 모두 포함된 줄이 있는지 확인)
            for note in special_list:
                if today_date in str(note) and name in str(note):
                    display_schedule = f"⭐ {note}"
                    is_special = True
                    break
            
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
else:
    st.warning("데이터가 비어있거나 시트 이름을 확인해 주세요!")
