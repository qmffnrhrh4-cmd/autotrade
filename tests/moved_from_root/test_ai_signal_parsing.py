"""
AI 신호 파싱 테스트 스크립트
다양한 조건으로 Gemini AI 응답 테스트 및 성공 조건 파악

문제: '\n "signal"' 파싱 오류 발생
목적: 성공하는 프롬프트/파싱 조합 찾기
"""

import os
import sys
import json
import re
import time
from typing import Dict, Any, Optional, Tuple
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("❌ google-generativeai 패키지가 설치되지 않았습니다")
    print("pip install google-generativeai")
    sys.exit(1)


class AISignalTester:
    """AI 신호 파싱 테스터"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models = {}
        self.test_results = []

    def initialize_models(self):
        """다양한 Gemini 모델 초기화"""
        genai.configure(api_key=self.api_key)

        model_names = [
            'gemini-2.5-flash',  # 우선순위 1: 최신 정식 모델 (Thinking 엔진 탑재)
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
        ]

        for model_name in model_names:
            try:
                self.models[model_name] = genai.GenerativeModel(model_name)
                print(f"✅ {model_name} 초기화 성공")
            except Exception as e:
                print(f"⚠️ {model_name} 초기화 실패: {e}")

    # ========== 프롬프트 전략 ==========

    def prompt_strategy_1_simple(self, stock_data: Dict[str, Any]) -> str:
        """전략 1: 극도로 간단한 프롬프트 + 명확한 JSON 요청"""
        return f"""Analyze this stock and respond ONLY with valid JSON (no explanations):

Stock: {stock_data['stock_name']} ({stock_data['stock_code']})
Price: {stock_data['current_price']:,} KRW
Change: {stock_data['change_rate']:+.2f}%

Required JSON format:
{{
  "signal": "buy",
  "confidence": 0.8,
  "reasons": ["reason 1", "reason 2"],
  "risks": ["risk 1"]
}}

Response (JSON only):"""

    def prompt_strategy_2_structured(self, stock_data: Dict[str, Any]) -> str:
        """전략 2: 구조화된 프롬프트 + JSON schema 명시"""
        return f"""You are a trading analyst. Analyze this Korean stock.

STOCK DATA:
- Name: {stock_data['stock_name']} ({stock_data['stock_code']})
- Current Price: {stock_data['current_price']:,} KRW
- Change Rate: {stock_data['change_rate']:+.2f}%
- Volume: {stock_data['volume']:,} shares

ANALYSIS REQUEST:
Provide a JSON response following this exact schema:

{{
  "signal": "buy" | "hold" | "sell",
  "confidence": 0.0-1.0,
  "reasons": ["string array"],
  "risks": ["string array"],
  "target_price": integer,
  "stop_loss": integer
}}

Your JSON response:
```json
"""

    def prompt_strategy_3_minimal_fields(self, stock_data: Dict[str, Any]) -> str:
        """전략 3: 최소 필드만 요청 (signal + confidence만)"""
        return f"""Stock: {stock_data['stock_name']} - {stock_data['current_price']:,} KRW ({stock_data['change_rate']:+.2f}%)

Respond with ONLY this JSON structure:
{{
  "signal": "buy",
  "confidence": 0.75
}}"""

    def prompt_strategy_4_guided(self, stock_data: Dict[str, Any]) -> str:
        """전략 4: 단계별 가이드 + JSON 생성"""
        return f"""Task: Analyze {stock_data['stock_name']} ({stock_data['stock_code']})

Step 1: Current price is {stock_data['current_price']:,} KRW, changed {stock_data['change_rate']:+.2f}%
Step 2: Determine if this is buy/hold/sell
Step 3: Rate confidence 0.0-1.0

Now output ONLY this JSON (no extra text):
{{
  "signal": "your decision",
  "confidence": your confidence
}}"""

    def prompt_strategy_5_example_driven(self, stock_data: Dict[str, Any]) -> str:
        """전략 5: 예제 기반 프롬프트"""
        return f"""Analyze this stock and respond like the example:

Example Input: Samsung Electronics - 70,000 KRW (+2.5%)
Example Output:
{{
  "signal": "buy",
  "confidence": 0.82,
  "reasons": ["Strong momentum", "High volume"]
}}

Your Input: {stock_data['stock_name']} - {stock_data['current_price']:,} KRW ({stock_data['change_rate']:+.2f}%)
Your Output:
"""

    # ========== JSON 파싱 전략 ==========

    def parse_strategy_1_simple(self, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """전략 1: 가장 간단한 {} 추출"""
        try:
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')

            if first_brace == -1 or last_brace == -1:
                return False, None, "No braces found"

            json_str = response_text[first_brace:last_brace+1]
            data = json.loads(json_str)
            return True, data, "Simple extraction successful"
        except Exception as e:
            return False, None, f"Simple extraction failed: {e}"

    def parse_strategy_2_code_block(self, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """전략 2: ```json 코드 블록 추출"""
        try:
            # Try ```json block
            match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                return True, data, "Code block (```json) extraction successful"

            # Try ``` block
            match = re.search(r'```\s*\n(.*?)\n```', response_text, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                if json_str.startswith('{'):
                    data = json.loads(json_str)
                    return True, data, "Code block (```) extraction successful"

            return False, None, "No code block found"
        except Exception as e:
            return False, None, f"Code block extraction failed: {e}"

    def parse_strategy_3_clean_and_parse(self, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """전략 3: 응답 정리 후 파싱"""
        try:
            # 1. 코드 블록 제거
            cleaned = re.sub(r'```json\s*\n', '', response_text)
            cleaned = re.sub(r'```\s*\n?', '', cleaned)

            # 2. 줄바꿈 정리
            cleaned = cleaned.strip()

            # 3. JSON 추출
            first_brace = cleaned.find('{')
            last_brace = cleaned.rfind('}')

            if first_brace == -1 or last_brace == -1:
                return False, None, "No JSON found after cleaning"

            json_str = cleaned[first_brace:last_brace+1]

            # 4. 잘못된 쉼표 제거
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)

            data = json.loads(json_str)
            return True, data, "Clean and parse successful"
        except Exception as e:
            return False, None, f"Clean and parse failed: {e}"

    def parse_strategy_4_line_by_line(self, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """전략 4: 줄별로 JSON 재구성"""
        try:
            lines = response_text.strip().split('\n')
            json_lines = []
            in_json = False

            for line in lines:
                if '{' in line:
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if '}' in line and in_json:
                    break

            if not json_lines:
                return False, None, "No JSON lines found"

            json_str = '\n'.join(json_lines)
            data = json.loads(json_str)
            return True, data, "Line-by-line reconstruction successful"
        except Exception as e:
            return False, None, f"Line-by-line failed: {e}"

    def parse_strategy_5_aggressive(self, response_text: str) -> Tuple[bool, Optional[Dict], str]:
        """전략 5: 공격적 파싱 (모든 전략 시도)"""
        strategies = [
            self.parse_strategy_2_code_block,
            self.parse_strategy_3_clean_and_parse,
            self.parse_strategy_1_simple,
            self.parse_strategy_4_line_by_line,
        ]

        for strategy in strategies:
            success, data, msg = strategy(response_text)
            if success:
                return True, data, f"Aggressive: {msg}"

        return False, None, "All aggressive strategies failed"

    # ========== 테스트 실행 ==========

    def run_single_test(
        self,
        model_name: str,
        prompt_strategy_name: str,
        prompt: str,
        parse_strategy_name: str,
        parse_func,
        stock_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """단일 테스트 실행"""

        test_name = f"{model_name} + {prompt_strategy_name} + {parse_strategy_name}"
        print(f"\n{'='*80}")
        print(f"🧪 테스트: {test_name}")
        print(f"{'='*80}")

        result = {
            'test_name': test_name,
            'model': model_name,
            'prompt_strategy': prompt_strategy_name,
            'parse_strategy': parse_strategy_name,
            'success': False,
            'signal': None,
            'confidence': None,
            'error': None,
            'response_preview': None,
            'response_length': 0,
            'execution_time': 0,
        }

        try:
            model = self.models.get(model_name)
            if not model:
                result['error'] = f"Model {model_name} not available"
                print(f"❌ {result['error']}")
                return result

            # API 호출
            print(f"📤 프롬프트 전송 중... (길이: {len(prompt)} chars)")
            start_time = time.time()

            response = model.generate_content(
                prompt,
                request_options={'timeout': 30}
            )

            execution_time = time.time() - start_time
            result['execution_time'] = execution_time

            # 응답 검증
            if not response.candidates:
                result['error'] = "No candidates in response"
                print(f"❌ {result['error']}")
                return result

            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason

            if finish_reason != 1:  # 1 = STOP (정상)
                reason_map = {2: "SAFETY", 3: "MAX_TOKENS", 4: "RECITATION", 5: "OTHER"}
                result['error'] = f"Blocked: {reason_map.get(finish_reason, finish_reason)}"
                print(f"❌ {result['error']}")
                return result

            response_text = response.text
            result['response_length'] = len(response_text)
            result['response_preview'] = response_text[:200]

            print(f"✅ API 응답 수신 ({execution_time:.2f}s, {len(response_text)} chars)")
            print(f"📝 응답 미리보기:\n{response_text[:300]}...")

            # JSON 파싱
            print(f"\n🔍 JSON 파싱 시도: {parse_strategy_name}")
            parse_success, parsed_data, parse_msg = parse_func(response_text)

            if parse_success:
                result['success'] = True
                result['signal'] = parsed_data.get('signal', 'N/A')
                result['confidence'] = parsed_data.get('confidence', 0)
                result['parsed_data'] = parsed_data

                print(f"✅ 파싱 성공! {parse_msg}")
                print(f"📊 신호: {result['signal']}, 신뢰도: {result['confidence']}")
                print(f"📋 전체 데이터: {json.dumps(parsed_data, indent=2, ensure_ascii=False)}")
            else:
                result['error'] = parse_msg
                print(f"❌ 파싱 실패: {parse_msg}")

                # 디버깅: 응답 전체 출력
                print(f"\n🔍 디버깅 - 전체 응답:\n{response_text}")

        except Exception as e:
            result['error'] = f"Exception: {str(e)}"
            print(f"❌ 예외 발생: {e}")
            import traceback
            traceback.print_exc()

        return result

    def run_comprehensive_test(self, stock_data: Dict[str, Any]):
        """종합 테스트 실행"""

        print("\n" + "="*80)
        print("🚀 AI 신호 파싱 종합 테스트 시작")
        print("="*80)
        print(f"테스트 종목: {stock_data['stock_name']} ({stock_data['stock_code']})")
        print(f"현재가: {stock_data['current_price']:,}원 ({stock_data['change_rate']:+.2f}%)")
        print("="*80)

        # 프롬프트 전략 목록
        prompt_strategies = [
            ('Simple', self.prompt_strategy_1_simple),
            ('Structured', self.prompt_strategy_2_structured),
            ('Minimal', self.prompt_strategy_3_minimal_fields),
            ('Guided', self.prompt_strategy_4_guided),
            ('Example', self.prompt_strategy_5_example_driven),
        ]

        # 파싱 전략 목록
        parse_strategies = [
            ('Aggressive', self.parse_strategy_5_aggressive),
            ('CodeBlock', self.parse_strategy_2_code_block),
            ('CleanParse', self.parse_strategy_3_clean_and_parse),
            ('Simple', self.parse_strategy_1_simple),
        ]

        # 모든 조합 테스트
        total_tests = 0
        successful_tests = 0

        for model_name in self.models.keys():
            for prompt_name, prompt_func in prompt_strategies:
                prompt = prompt_func(stock_data)

                for parse_name, parse_func in parse_strategies:
                    result = self.run_single_test(
                        model_name,
                        prompt_name,
                        prompt,
                        parse_name,
                        parse_func,
                        stock_data
                    )

                    self.test_results.append(result)
                    total_tests += 1

                    if result['success']:
                        successful_tests += 1
                        print(f"\n✅ 성공! ({successful_tests}/{total_tests})")
                    else:
                        print(f"\n❌ 실패 ({successful_tests}/{total_tests})")

                    # API 부하 방지
                    time.sleep(2)

        # 결과 요약
        self.print_summary()

    def run_quick_test(self, stock_data: Dict[str, Any]):
        """빠른 테스트 (성공 가능성 높은 조합만)"""

        print("\n" + "="*80)
        print("⚡ AI 신호 파싱 빠른 테스트")
        print("="*80)
        print(f"테스트 종목: {stock_data['stock_name']}")
        print("="*80)

        # 우선순위가 높은 조합 (2.5 Flash 우선)
        test_configs = [
            ('gemini-2.5-flash', 'Simple', self.prompt_strategy_1_simple, 'Aggressive', self.parse_strategy_5_aggressive),
            ('gemini-2.5-flash', 'Minimal', self.prompt_strategy_3_minimal_fields, 'Aggressive', self.parse_strategy_5_aggressive),
            ('gemini-2.5-flash', 'Structured', self.prompt_strategy_2_structured, 'CodeBlock', self.parse_strategy_2_code_block),
            ('gemini-2.0-flash-exp', 'Simple', self.prompt_strategy_1_simple, 'Aggressive', self.parse_strategy_5_aggressive),
        ]

        for model_name, prompt_name, prompt_func, parse_name, parse_func in test_configs:
            if model_name not in self.models:
                continue

            prompt = prompt_func(stock_data)
            result = self.run_single_test(
                model_name,
                prompt_name,
                prompt,
                parse_name,
                parse_func,
                stock_data
            )

            self.test_results.append(result)

            if result['success']:
                print(f"\n✅✅✅ 성공한 조합 발견! ✅✅✅")
                print(f"모델: {model_name}")
                print(f"프롬프트: {prompt_name}")
                print(f"파싱: {parse_name}")
                print(f"신호: {result['signal']}, 신뢰도: {result['confidence']}")
                return result

            time.sleep(2)

        print(f"\n⚠️ 모든 빠른 테스트 실패")
        self.print_summary()

    def print_summary(self):
        """테스트 결과 요약"""

        print("\n\n" + "="*80)
        print("📊 테스트 결과 요약")
        print("="*80)

        total = len(self.test_results)
        successful = [r for r in self.test_results if r['success']]
        failed = [r for r in self.test_results if not r['success']]

        print(f"\n총 테스트: {total}개")
        print(f"✅ 성공: {len(successful)}개 ({len(successful)/total*100:.1f}%)")
        print(f"❌ 실패: {len(failed)}개 ({len(failed)/total*100:.1f}%)")

        if successful:
            print(f"\n✅ 성공한 조합들:")
            for r in successful:
                print(f"  - {r['test_name']}")
                print(f"    신호: {r['signal']}, 신뢰도: {r['confidence']}, 시간: {r['execution_time']:.2f}s")

        if failed:
            print(f"\n❌ 실패 원인 분석:")
            error_counts = {}
            for r in failed:
                error = r.get('error', 'Unknown')
                error_counts[error] = error_counts.get(error, 0) + 1

            for error, count in sorted(error_counts.items(), key=lambda x: -x[1]):
                print(f"  - {error}: {count}건")

        # 최고의 조합 추천
        if successful:
            best = min(successful, key=lambda x: x['execution_time'])
            print(f"\n🏆 추천 조합 (가장 빠른 성공):")
            print(f"  모델: {best['model']}")
            print(f"  프롬프트 전략: {best['prompt_strategy']}")
            print(f"  파싱 전략: {best['parse_strategy']}")
            print(f"  실행 시간: {best['execution_time']:.2f}s")

        # 결과를 JSON 파일로 저장
        with open('ai_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 상세 결과가 ai_test_results.json에 저장되었습니다")


def main():
    """메인 함수"""

    # API 키 확인 (환경변수 또는 config에서)
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        # config에서 가져오기 시도
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from config import GEMINI_API_KEY
            api_key = GEMINI_API_KEY
            print(f"✅ config에서 API 키 로드 성공")
        except Exception as e:
            print(f"❌ API 키를 찾을 수 없습니다: {e}")
            print("환경변수 또는 config.py에 GEMINI_API_KEY를 설정하세요")
            sys.exit(1)

    if not api_key:
        print("❌ GEMINI_API_KEY가 비어있습니다")
        sys.exit(1)

    # 테스트 데이터
    test_stock = {
        'stock_name': '삼성전자',
        'stock_code': '005930',
        'current_price': 70000,
        'change_rate': 2.5,
        'volume': 10000000,
    }

    # 테스터 초기화
    tester = AISignalTester(api_key)
    tester.initialize_models()

    if not tester.models:
        print("❌ 사용 가능한 모델이 없습니다")
        sys.exit(1)

    # 실행 모드 선택
    print("\n테스트 모드 선택:")
    print("1. 빠른 테스트 (4개 조합, ~1분)")
    print("2. 종합 테스트 (모든 조합, ~10분)")
    print("3. 커스텀 테스트 (직접 입력)")

    try:
        mode = input("\n선택 (1/2/3): ").strip()
    except:
        mode = "1"  # 기본값

    if mode == "2":
        tester.run_comprehensive_test(test_stock)
    elif mode == "3":
        print("\n커스텀 테스트 - 종목 정보 입력:")
        try:
            stock_name = input("종목명 (기본: 삼성전자): ").strip() or "삼성전자"
            stock_code = input("종목코드 (기본: 005930): ").strip() or "005930"
            current_price = int(input("현재가 (기본: 70000): ").strip() or "70000")
            change_rate = float(input("변동률 (기본: 2.5): ").strip() or "2.5")

            custom_stock = {
                'stock_name': stock_name,
                'stock_code': stock_code,
                'current_price': current_price,
                'change_rate': change_rate,
                'volume': 10000000,
            }
            tester.run_quick_test(custom_stock)
        except Exception as e:
            print(f"❌ 입력 오류: {e}")
            print("기본 데이터로 테스트 진행...")
            tester.run_quick_test(test_stock)
    else:
        tester.run_quick_test(test_stock)


if __name__ == '__main__':
    main()
