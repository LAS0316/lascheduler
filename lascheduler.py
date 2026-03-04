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
            special_list = sheet2.col_values(1)[1:] 
        except:
            special_list = []
            
        return df_fixed, special_list
        
    except Exception as e:
        st.error(f"❌ 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame(), []

# 데이터 불러오기
df_fixed, special_list = get_las_data()

st.title("📅 lascheduler : 팀 실시간 시간표")

# --- 화면 상단: 동기화 버튼 ---
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 데이터 즉시 동기화", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.link_button("📝 캘린더 시트 수정하러 가기", "https://docs.google.com/spreadsheets/d/139YrVpzvovwhOnyDDtHhYpYmL8etgJDw4NzKWQKET1o/edit?gid=0#gid=0", use_container_width=True)

# --- 메인 대시보드 UI ---
if not df_fixed.empty:
    
    now = datetime.datetime.now()
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    today_name = days[now.weekday()]
    today_date = f"{now.month}/{now.day}" # '3/4' 형태

    st.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M')} ({today_name})")

    st.subheader("👥 멤버 실시간 상태")
    
    # 🔥 변경된 부분: 3명 기준으로 줄바꿈하는 로직
    for i, row in df_fixed.iterrows():
        # 인덱스(i)가 3의 배수일 때마다 새로운 3칸짜리 가로줄을 만듭니다.
        if i % 3 == 0:
            cols = st.columns(3)
            
        # 0, 1, 2번은 각각 첫 번째 줄의 0, 1, 2열에 들어갑니다.
        with cols[i % 3]:
            name = str(row.get("이름", f"멤버{i+1}"))
            
            # 기본 일정 (고정 일정 탭)
            display_schedule = str(row.get(today_name, "자유"))
            is_special = False
            
            # 특수 일정 체크
            for note in special_list:
                if today_date in str(note) and name in str(note):
                    display_schedule = f"⭐ {note}"
                    is_special = True
                    break
            
            # 🔥 변경된 부분: 배경색을 더 찐하게, 다크모드에서도 눈에 띄게!
            if any(kw in display_schedule for kw in ["수업", "알바", "개인일정"]):
                bg_color = "#ff8a80"  # 더 진해진 빨간색
                text_color = "#b71c1c" # 아주 딥한 빨간 글씨
                status_text = "부재 중"
            elif "자유" in display_schedule or not display_schedule.strip():
                bg_color = "#a5d6a7"  # 더 진해진 초록색
                text_color = "#1b5e20" # 아주 딥한 초록 글씨
                status_text = "활동 가능"
            else:
                bg_color = "#ffe082"  # 더 진해진 노란색
                text_color = "#e65100" # 아주 딥한 주황 글씨
                status_text = "확인 필요"
                
            # 🔥 변경된 부분: Flexbox를 이용한 완벽한 상하좌우 가운데 정렬
            st.markdown(f"""
            <div style='
                display: flex; 
                flex-direction: column; 
                justify-content: center; 
                align-items: center; 
                border-radius: 12px; 
                padding: 20px 10px; 
                margin-bottom: 5px; 
                background-color: {bg_color}; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                height: 110px;
            '>
                <h2 style='margin: 0; padding-bottom: 5px; font-size: 1.8rem; color: #111; text-align: center;'>{name}</h2>
                <div style='font-size: 1.2rem; font-weight: 900; color: {text_color}; text-align: center;'>{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 아래에 뜨는 세부 일정도 가운데로 예쁘게 정렬했습니다.
            if is_special:
                st.warning(display_schedule)
            else:
                st.caption(f"<div style='text-align: center; margin-bottom: 15px;'>일정: {display_schedule}</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🗓️ 주간 고정 일정표")
    st.dataframe(df_fixed, use_container_width=True)
else:
    st.warning("데이터가 비어있거나 시트 이름을 확인해 주세요!")
