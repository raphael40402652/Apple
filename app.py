%%writefile app.py
import streamlit as st
import fitz
import google.generativeai as genai
import time

st.set_page_config(page_title="의대 강의록 구조화 도구", page_icon="🩺", layout="wide")
st.title("🩺 의대 강의록 지식 구조화 엔진")
st.markdown("단순 요약을 넘어, 강의 내용을 의학적 로직에 따라 유기적으로 재구성합니다.")

api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

if api_key:
    genai.configure(api_key=api_key)

uploaded_file = st.file_uploader("PDF 강의 자료 업로드", type=["pdf"])

if uploaded_file and api_key:
    if st.button("지식 구조화 시작 🚀"):
        with st.spinner("강의록 분석 중..."):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            
            # 누락 방지를 위해 분석 범위를 조금 더 넓힙니다 (약 8000자)
            context_text = full_text[:8000] 

        with st.spinner("유기적 요약 및 표 생성 중..."):
            # 프롬프트를 더 구체적이고 유기적으로 수정했습니다.
            system_prompt = """
            너는 의과대학 본과 학생의 학습 효율을 극대화하는 전문 튜터야.
            입력된 강의 내용을 단순 나열하지 말고, 다음 원칙에 따라 '멀티 섹션 표'로 정리해줘.

            [정리 원칙]
            1. 섹션 분리: 한 표에 다 넣지 말고 주제(예: 해부학적 구조, 질병의 기전, 감별 진단, 약물 치료 등)별로 표를 나누어라.
            2. 유기적 연결: 병태생리 칸에서는 원인과 결과의 인과관계를 화살표(->) 등을 사용하여 논리적으로 설명하라.
            3. 누락 방지: 사소해 보이는 임상적 진주(Clinical Pearls)나 감별 포인트도 '비고'나 '특징' 칸을 만들어 포함시켜라.
            4. 가독성: 표 형식을 사용하되, 표 아래에 핵심적인 인과관계를 설명하는 짧은 한 줄 요약을 덧붙여라.
            """
            
            try:
                model = genai.GenerativeModel(
                    model_name='models/gemini-flash-latest', 
                    system_instruction=system_prompt,
                    generation_config={"temperature": 0.3} # 약간의 추론을 위해 온도를 살짝 높임
                )
                
                response = model.generate_content(context_text)
                
                st.success("구조화가 완료되었습니다!")
                
                # 결과 출력
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"오류 발생: {e}")
