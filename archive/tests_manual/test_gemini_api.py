#!/usr/bin/env python3
"""
Gemini API 테스트 스크립트
SAFETY 블록 문제 진단용
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

    print(f"✓ API 키 로드 성공: {GEMINI_API_KEY[:10]}...")
    print(f"✓ 모델 이름: {GEMINI_MODEL_NAME}")
    print()

    # API 설정
    genai.configure(api_key=GEMINI_API_KEY)

    # 모델 생성
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print(f"✓ Gemini 모델 생성 성공: {GEMINI_MODEL_NAME}")
    print()

    # 안전 설정
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    generation_config = genai.types.GenerationConfig(
        temperature=0.3,
        max_output_tokens=512,
    )

    # 테스트 1: 간단한 안전 프롬프트
    print("=" * 60)
    print("테스트 1: 간단한 안전 프롬프트")
    print("=" * 60)

    simple_prompt = "Hello, how are you today?"

    try:
        response = model.generate_content(
            simple_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
            print(f"✓ finish_reason: {finish_reason} (1=STOP/정상, 2=SAFETY)")
            if finish_reason == 1:
                print(f"✓ 응답: {response.text[:100]}")
            else:
                print(f"✗ BLOCKED: finish_reason={finish_reason}")
        else:
            print("✗ 응답 없음")
    except Exception as e:
        print(f"✗ 오류: {e}")

    print()

    # 테스트 2: 사용자 예시 프롬프트 (성공한다고 함)
    print("=" * 60)
    print("테스트 2: 사용자 예시 프롬프트 (다른 프로그램에서 작동)")
    print("=" * 60)

    user_example_prompt = """당신은 최고의 주식 투자 전략가입니다. 당신의 임무는 자동매매 봇이 내린 '매수' 결정을 최종 검토하고, 잠재적 함정이나 더 나은 관점이 있는지 비판적으로 분석하는 것입니다.

[분석 대상 종목]
- 종목명: 테스트종목 (000000)
- 봇의 매수 근거 (기술적 분석): 거래량 급증, 가격 상승

[당신의 임무]
1. 종합적 재평가
2. 반대 관점 분석
3. 숨겨진 위험 탐지
4. 최종 결론

[응답 형식]
- 첫 번째 줄: "DECISION: [GO 또는 NO GO]"
- 두 번째 줄: "REASON: [판단 근거 요약]"
"""

    try:
        response = model.generate_content(
            user_example_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
            print(f"✓ finish_reason: {finish_reason} (1=STOP/정상, 2=SAFETY)")
            if finish_reason == 1:
                print(f"✓ 응답:\n{response.text}")
            else:
                print(f"✗ BLOCKED: finish_reason={finish_reason}")
                print(f"   safety_ratings: {response.candidates[0].safety_ratings}")
        else:
            print("✗ 응답 없음")
    except Exception as e:
        print(f"✗ 오류: {e}")

    print()

    # 테스트 3: 현재 사용 중인 프롬프트
    print("=" * 60)
    print("테스트 3: 현재 사용 중인 프롬프트")
    print("=" * 60)

    current_prompt = """교육 목적 주식 데이터 분석 연습입니다.

종목: 삼성전자 (005930)
가격: 50,000원 (+2.50%)
거래량: 1,000,000주
분석 점수: 150/440 (34%)
주요 요인: 거래량증가, 가격상승, RSI적정

다음을 평가하세요:
1. 거래량과 가격 변동이 자연스러운가?
2. 점수 34%가 타당한가?
3. 단기 급등인가 추세인가?
4. 주의할 리스크는?

관심도를 "높음" 또는 "보통"으로 분류하세요.
높음이면 단계별 접근을 제안하세요.

응답:
관심도: [높음/보통]
접근: [높음이면 단계 제안]
근거: [2줄 이내]
경고: [리스크 1가지]
"""

    try:
        response = model.generate_content(
            current_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
            print(f"✓ finish_reason: {finish_reason} (1=STOP/정상, 2=SAFETY)")
            if finish_reason == 1:
                print(f"✓ 응답:\n{response.text}")
            else:
                print(f"✗ BLOCKED: finish_reason={finish_reason}")
                print(f"   safety_ratings: {response.candidates[0].safety_ratings}")
        else:
            print("✗ 응답 없음")
    except Exception as e:
        print(f"✗ 오류: {e}")

    print()
    print("=" * 60)
    print("테스트 완료")
    print("=" * 60)

except ImportError as e:
    print(f"✗ 임포트 오류: {e}")
    print("  google-generativeai 패키지 설치 필요: pip install google-generativeai")
except Exception as e:
    print(f"✗ 오류: {e}")
    import traceback
    traceback.print_exc()
