import streamlit as st
import fitz
import google.generativeai as genai
import time

# 1. 화면 UI 설정
st.set_page_config(page_title="의대 강의록 요약기", page_icon="🩺")
st.title("🩺 의대 강의록 자동 요약기")
st.markdown("본과 1학년 수업 PDF를 올리면, 암기하기 편한 표로 정리해 줍니다.")

# 2. API 키 입력 (보안을 위해 화면에서 직접 입력받습니다)
api_key = st.text_input("Gemini API 키를 입력하세요 (안전하게 처리됩니다)", type="password")

if api_key:
    genai.configure(api_key=api_key)

# 3. 파일 업로드 창
uploaded_file = st.file_uploader("PDF 강의 자료를 드래그 앤 드롭 하세요", type=["pdf"])

if uploaded_file and api_key:
    if st.button("요약 시작하기 🚀"):
        # 텍스트 추출 단계
        with st.spinner("PDF에서 텍스트를 추출하는 중입니다..."):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            
            # 테스트를 위해 우선 앞부분 3000자만 추출합니다.
            test_text = full_text[:3000] 

        # LLM 요약 단계
        with st.spinner("Gemini가 의학 용어를 분석하고 표를 그리는 중입니다..."):
            system_prompt = """
            너는 의과대학 본과 1학년 학생의 학습을 돕는 뛰어난 조교야.
            입력된 강의 텍스트를 분석해서 '질병명', '원인/병태생리', '임상증상', '진단', '치료' 등을 기준으로 정리해줘.
            [엄격한 제약조건]
            1. 반드시 Markdown 형식의 표(Table)로만 출력할 것.
            2. 표의 행(Row)과 열(Column)이 깨지지 않도록 마크다운 문법을 지킬 것.
            3. 각 칸의 내용은 줄글이 아닌 핵심 키워드 위주로 간결하게 요약할 것.
            """
            
            try:
                model = genai.GenerativeModel(
                    model_name='models/gemini-2.5-flash', 
                    system_instruction=system_prompt,
                    generation_config={"temperature": 0.2}
                )
                time.sleep(2) # API 호출 제한 방지
                response = model.generate_content(test_text)
                
                st.success("요약 완료! 아래 표를 확인하세요.")
                st.markdown(response.text) # 화면에 예쁜 마크다운 표 출력
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
elif not api_key:
    st.info("위 칸에 API 키를 먼저 입력해 주세요.")
