"""
ai/gemini_analyzer.py
Google Gemini AI 분석기
"""
import logging
import time
from typing import Dict, Any, Optional
from .base_analyzer import BaseAnalyzer
from utils.prompt_loader import load_prompt
from config.constants import AI_MODELS, DEFAULT_CACHE_TTL

logger = logging.getLogger(__name__)


class GeminiAnalyzer(BaseAnalyzer):
    """
    Google Gemini AI 분석기

    Gemini API를 사용한 종목/시장 분석
    """

    def __init__(self, api_key: str = None, model_name: str = None, enable_cross_check: bool = False):
        """
        Gemini 분석기 초기화

        Args:
            api_key: Gemini API 키
            model_name: 모델 이름 (기본: gemini-2.5-flash)
            enable_cross_check: 크로스 체크 활성화 (2.0 vs 2.5 비교)
        """
        super().__init__("GeminiAnalyzer")

        # API 설정
        if api_key is None:
            from config import GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_ENABLE_CROSS_CHECK
            self.api_key = GEMINI_API_KEY
            self.model_name = model_name or GEMINI_MODEL_NAME or AI_MODELS['primary']
            if enable_cross_check is False and GEMINI_ENABLE_CROSS_CHECK:
                enable_cross_check = GEMINI_ENABLE_CROSS_CHECK
        else:
            self.api_key = api_key
            self.model_name = model_name or AI_MODELS['primary']

        self.model = None

        # 크로스 체크 설정
        self.enable_cross_check = enable_cross_check
        self.model_2_0 = None
        self.model_2_5 = None

        # AI 분석 TTL 캐시
        self._analysis_cache = {}
        self._cache_ttl = DEFAULT_CACHE_TTL

        cross_check_status = "크로스체크 활성화" if enable_cross_check else "단일 모델"
        logger.info(f"GeminiAnalyzer 초기화 (모델: {self.model_name}, {cross_check_status})")

    def initialize(self) -> bool:
        """
        Gemini API 초기화

        Returns:
            초기화 성공 여부
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)

            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"기본 모델 초기화: {self.model_name}")

            if self.enable_cross_check:
                try:
                    self.model_2_0 = genai.GenerativeModel(AI_MODELS['secondary'])
                    logger.info(f"크로스체크 모델 초기화: {AI_MODELS['secondary']}")
                except Exception as e:
                    logger.warning(f"2.0 모델 초기화 실패: {e}")

                try:
                    self.model_2_5 = genai.GenerativeModel(AI_MODELS['primary'])
                    logger.info(f"크로스체크 모델 초기화: {AI_MODELS['primary']}")
                except Exception as e:
                    logger.warning(f"2.5 모델 초기화 실패: {e}")

                if not self.model_2_0 and not self.model_2_5:
                    logger.error("크로스체크 모델 초기화 모두 실패")
                    return False

            self.is_initialized = True
            logger.info("Gemini API 초기화 성공")
            return True

        except ImportError:
            logger.error("google-generativeai 패키지가 설치되지 않았습니다")
            logger.error("pip install google-generativeai 실행 필요")
            return False
        except Exception as e:
            logger.error(f"Gemini API 초기화 실패: {e}")
            return False

    def analyze_stock(
        self,
        stock_data: Dict[str, Any],
        analysis_type: str = 'comprehensive',
        score_info: Dict[str, Any] = None,
        portfolio_info: str = None
    ) -> Dict[str, Any]:
        """
        종목 분석

        Args:
            stock_data: 종목 데이터
            analysis_type: 분석 유형
            score_info: 점수 정보 (score, percentage, breakdown)
            portfolio_info: 현재 포트폴리오 정보

        Returns:
            분석 결과
        """
        if not self.is_initialized:
            if not self.initialize():
                return self._get_error_result("분석기 초기화 실패")

        is_valid, msg = self.validate_stock_data(stock_data)
        if not is_valid:
            return self._get_error_result(msg)

        stock_code = stock_data.get('stock_code', '')
        score = score_info.get('score', 0) if score_info else 0
        cache_key = f"{stock_code}_{int(score)}"

        if self.enable_cross_check:
            cache_key += "_crosscheck"

        if cache_key in self._analysis_cache:
            cached_entry = self._analysis_cache[cache_key]
            cached_time = cached_entry['timestamp']
            cached_result = cached_entry['result']

            if (time.time() - cached_time) < self._cache_ttl:
                logger.info(f"AI 분석 캐시 히트: {stock_code} (캐시 유효시간: {int(self._cache_ttl - (time.time() - cached_time))}초)")
                return cached_result
            else:
                del self._analysis_cache[cache_key]
                logger.info(f"AI 분석 캐시 만료: {stock_code}")

        start_time = time.time()

        # 크로스 체크 모드
        if self.enable_cross_check and self.model_2_0 and self.model_2_5:
            logger.info(f"🔀 크로스체크 분석 시작: {stock_code}")

            prompt = self._prepare_stock_prompt(stock_data, score_info, portfolio_info)

            result_2_0 = self._analyze_with_single_model(
                self.model_2_0,
                AI_MODELS['secondary'],
                prompt,
                stock_data
            )

            result_2_5 = self._analyze_with_single_model(
                self.model_2_5,
                AI_MODELS['primary'],
                prompt,
                stock_data
            )

            result = self._cross_check_results(result_2_0, result_2_5)

            self._analysis_cache[cache_key] = {
                'timestamp': time.time(),
                'result': result
            }

            elapsed_time = time.time() - start_time
            self.update_statistics(True, elapsed_time)

            if 'cross_check' in result:
                cc = result['cross_check']
                if cc.get('agreement'):
                    logger.info(f"크로스체크 일치: {result['signal']} (신뢰도: {result['confidence']})")
                else:
                    logger.info(f"크로스체크 불일치 → 보수적 선택: {result['signal']}")

            logger.info(
                f"크로스체크 분석 완료: {stock_code} "
                f"(신호: {result['signal']}, 신뢰도: {result['confidence']})"
            )

            return result

        # 일반 분석 모드 (단일 모델)
        max_retries = 5
        retry_delay = 3

        for attempt in range(max_retries):
            try:
                prompt = self._prepare_stock_prompt(stock_data, score_info, portfolio_info)

                response = self.model.generate_content(
                    prompt,
                    request_options={'timeout': 60}
                )

                if not response.candidates:
                    raise ValueError("Gemini API returned no candidates")

                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason

                if finish_reason != 1:
                    reason_map = {2: "SAFETY", 3: "MAX_TOKENS", 4: "RECITATION", 5: "OTHER"}
                    reason_name = reason_map.get(finish_reason, f"UNKNOWN({finish_reason})")
                    raise ValueError(f"Gemini blocked: {reason_name}")

                if not hasattr(response, 'text'):
                    raise ValueError("Gemini API response has no 'text' attribute")

                response_text = response.text
                if not response_text or len(response_text.strip()) == 0:
                    raise ValueError("Gemini API returned empty response")

                result = self._parse_stock_analysis_response(response_text, stock_data)

                self._analysis_cache[cache_key] = {
                    'timestamp': time.time(),
                    'result': result
                }
                logger.info(f"AI 분석 결과 캐시 저장: {stock_code} (TTL: {self._cache_ttl}초)")

                elapsed_time = time.time() - start_time
                self.update_statistics(True, elapsed_time)

                logger.info(
                    f"종목 분석 완료: {stock_data.get('stock_code')} "
                    f"(점수: {result['score']}, 신호: {result['signal']})"
                )

                return result

            except Exception as e:
                error_msg = str(e)

                if attempt < max_retries - 1:
                    logger.warning(
                        f"AI 분석 실패 (시도 {attempt+1}/{max_retries}), "
                        f"{retry_delay}초 후 재시도: {error_msg}"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"AI 분석 최종 실패 ({max_retries}회 시도): {error_msg}")
                    self.update_statistics(False)
                    return self._get_error_result(f"AI 분석 실패: {error_msg}")

    def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        시장 분석

        Args:
            market_data: 시장 데이터

        Returns:
            시장 분석 결과
        """
        if not self.is_initialized:
            if not self.initialize():
                return self._get_error_result("분석기 초기화 실패")

        start_time = time.time()

        try:
            prompt = self._create_market_analysis_prompt(market_data)
            response = self.model.generate_content(prompt)
            result = self._parse_market_analysis_response(response.text)

            elapsed_time = time.time() - start_time
            self.update_statistics(True, elapsed_time)

            logger.info(f"시장 분석 완료 (심리: {result['market_sentiment']})")

            return result

        except Exception as e:
            logger.error(f"시장 분석 중 오류: {e}")
            self.update_statistics(False)
            return self._get_error_result(str(e))

    def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        포트폴리오 분석

        Args:
            portfolio_data: 포트폴리오 데이터

        Returns:
            포트폴리오 분석 결과
        """
        if not self.is_initialized:
            if not self.initialize():
                return self._get_error_result("분석기 초기화 실패")

        start_time = time.time()

        try:
            prompt = self._create_portfolio_analysis_prompt(portfolio_data)
            response = self.model.generate_content(prompt)
            result = self._parse_portfolio_analysis_response(response.text)

            elapsed_time = time.time() - start_time
            self.update_statistics(True, elapsed_time)

            logger.info("포트폴리오 분석 완료")

            return result

        except Exception as e:
            logger.error(f"포트폴리오 분석 중 오류: {e}")
            self.update_statistics(False)
            return self._get_error_result(str(e))

    # ==================== 프롬프트 생성 ====================

    def _prepare_stock_prompt(
        self,
        stock_data: Dict[str, Any],
        score_info: Dict[str, Any] = None,
        portfolio_info: str = None
    ) -> str:
        """종목 분석 프롬프트 준비"""
        prompt_template = load_prompt('stock_analysis_simple')

        if score_info:
            score = score_info.get('score', 0)
            percentage = score_info.get('percentage', 0)
            breakdown = score_info.get('breakdown', {})
            score_breakdown_detailed = "\n".join([
                f"  {k}: {v:.1f}점" for k, v in breakdown.items() if v >= 0
            ])
        else:
            score = 0
            percentage = 0
            score_breakdown_detailed = "  점수 정보 없음"

        portfolio_text = portfolio_info or "보유 종목 없음"

        institutional_net_buy = stock_data.get('institutional_net_buy', 0)
        foreign_net_buy = stock_data.get('foreign_net_buy', 0)
        bid_ask_ratio = stock_data.get('bid_ask_ratio', 1.0)

        return prompt_template.format(
            stock_name=stock_data.get('stock_name', ''),
            stock_code=stock_data.get('stock_code', ''),
            current_price=stock_data.get('current_price', 0),
            change_rate=stock_data.get('change_rate', 0.0),
            volume=stock_data.get('volume', 0),
            score=score,
            percentage=percentage,
            score_breakdown_detailed=score_breakdown_detailed,
            institutional_net_buy=institutional_net_buy,
            foreign_net_buy=foreign_net_buy,
            bid_ask_ratio=bid_ask_ratio,
            portfolio_info=portfolio_text
        )

    def _create_market_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """시장 분석 프롬프트 생성"""
        kospi = market_data.get('kospi', {})
        kosdaq = market_data.get('kosdaq', {})

        prompt = f"""당신은 한국 주식시장 전문 애널리스트입니다. 현재 시장을 분석하세요.

## 📊 시장 지표

**KOSPI**:
- 현재: {kospi.get('index', 0):.2f} ({kospi.get('change_rate', 0):+.2f}%)
- 거래대금: {kospi.get('trading_value', 0):,}억원
- 외국인: {kospi.get('foreign_net', 0):,}억원

**KOSDAQ**:
- 현재: {kosdaq.get('index', 0):.2f} ({kosdaq.get('change_rate', 0):+.2f}%)
- 거래대금: {kosdaq.get('trading_value', 0):,}억원

---

## 🎯 분석 요청

**5가지 관점**에서 분석:

1. **시장 레짐**: Bull/Bear/Sideways/Transitioning
2. **투자 심리**: Euphoria/Greed/Neutral/Fear/Panic
3. **스마트머니**: 외국인/기관 매집 또는 분산
4. **섹터 로테이션**: 강세/약세 업종
5. **단기 전략**: 공격 매수/선별 매수/관망/현금 확대

**JSON 형식으로 응답:**

```json
{{
  "market_regime": "Bull Market" | "Bear Market" | "Sideways" | "Transitioning",
  "market_sentiment": "Euphoria" | "Greed" | "Neutral" | "Fear" | "Panic",
  "market_score": <0-10>,

  "smart_money_flow": {{
    "foreign_trend": "Strong Buy" | "Buy" | "Neutral" | "Sell" | "Strong Sell",
    "comment": "스마트머니 해석 (1-2문장)"
  }},

  "trading_strategy": "Aggressive Buy" | "Selective Buy" | "Hold" | "Increase Cash",

  "key_insights": ["인사이트 1", "인사이트 2", "인사이트 3"],
  "risks": ["리스크 1", "리스크 2"],
  "detailed_analysis": "시장 종합 분석 (3-5문장)"
}}
```"""

        return prompt

    def _create_portfolio_analysis_prompt(self, portfolio_data: Dict[str, Any]) -> str:
        """포트폴리오 분석 프롬프트 생성"""
        holdings = portfolio_data.get('holdings', [])
        total_assets = portfolio_data.get('total_assets', 0)

        prompt = f"""당신은 포트폴리오 리스크 관리 전문가입니다. **리스크 관점**에서 분석하세요.

## 📊 포트폴리오 현황

**자산 구성**:
- 총 자산: {total_assets:,}원
- 현금 비중: {portfolio_data.get('cash_ratio', 0):.1f}%
- 주식 비중: {100 - portfolio_data.get('cash_ratio', 0):.1f}%
- 보유 종목: {portfolio_data.get('position_count', 0)}개
- 총 수익률: {portfolio_data.get('total_profit_loss_rate', 0):+.2f}%

**보유 종목**:
{self._format_holdings_data(holdings)}

---

## 🎯 분석 요청

**6가지 영역** 분석:

1. **포트폴리오 구성**: 현금/주식 비중 적절성
2. **집중도 리스크**: 특정 종목 과도 집중 여부
3. **업종 다각화**: 업종 분산 적절성
4. **수익률 분석**: 주요 기여/악화 종목
5. **손절 필요성**: 손실 종목 중 손절 필요 종목
6. **리밸런싱**: 비중 조정 필요 종목

**JSON 형식으로 응답:**

```json
{{
  "overall_health": "Excellent" | "Good" | "Fair" | "Poor",
  "risk_level": "Very High" | "High" | "Medium" | "Low",

  "concentration_risk": {{
    "level": "Very High" | "High" | "Medium" | "Low",
    "comment": "집중도 평가 (1-2문장)"
  }},

  "actions_required": {{
    "stop_loss_candidates": ["종목명 (이유)"],
    "reduce_position": ["종목명"],
    "increase_position": ["종목명"]
  }},

  "strengths": ["강점 1", "강점 2"],
  "weaknesses": ["약점 1", "약점 2"],
  "key_recommendations": ["추천 1", "추천 2", "추천 3"],
  "detailed_analysis": "포트폴리오 종합 분석 (3-5문장)"
}}
```"""

        return prompt

    # ==================== 응답 파싱 ====================

    def _parse_stock_analysis_response(
        self,
        response_text: str,
        stock_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """종목 분석 응답 파싱 - JSON 또는 텍스트 형식 모두 지원"""

        if not response_text:
            logger.error("빈 응답 텍스트를 받았습니다")
            raise ValueError("Empty response text")

        try:
            import re
            import json

            cleaned_text = response_text.strip()
            json_str = None

            json_match = re.search(r'```json\s*\n(.*?)\n```', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

            if not json_str:
                json_match = re.search(r'```\s*\n(.*?)\n```', cleaned_text, re.DOTALL)
                if json_match:
                    potential_json = json_match.group(1).strip()
                    if potential_json.startswith('{'):
                        json_str = potential_json

            if not json_str:
                pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
                json_blocks = re.findall(pattern, cleaned_text, re.DOTALL)

                if not json_blocks:
                    first_brace = cleaned_text.find('{')
                    last_brace = cleaned_text.rfind('}')
                    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                        json_str = cleaned_text[first_brace:last_brace+1]
                elif json_blocks:
                    json_str = max(json_blocks, key=len)

            if not json_str:
                if cleaned_text.startswith('{'):
                    json_str = cleaned_text

            if json_str:
                try:
                    json_str = json_str.strip()
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)

                    data = json.loads(json_str)

                    signal_map = {
                        'STRONG_BUY': 'buy',
                        'BUY': 'buy',
                        'WEAK_BUY': 'buy',
                        'HOLD': 'hold',
                        'WEAK_SELL': 'sell',
                        'SELL': 'sell',
                        'STRONG_SELL': 'sell'
                    }

                    signal = signal_map.get(str(data.get('signal', 'HOLD')).upper(), 'hold')

                    reasons = []
                    if 'detailed_reasoning' in data:
                        reasons.append(data['detailed_reasoning'])
                    if 'key_insights' in data and isinstance(data.get('key_insights'), list):
                        reasons.extend(data['key_insights'])

                    warnings = data.get('warnings', [])
                    if isinstance(warnings, str):
                        warnings = [warnings]

                    trading_plan = data.get('trading_plan', {})
                    entry_strategy = trading_plan.get('entry_strategy', '') if isinstance(trading_plan, dict) else ''

                    current_price = stock_data.get('current_price', 0)

                    target_price = current_price
                    stop_loss_price = current_price

                    if isinstance(trading_plan, dict):
                        take_profit_targets = trading_plan.get('take_profit_targets', [])
                        if isinstance(take_profit_targets, list) and len(take_profit_targets) > 0:
                            first_target = take_profit_targets[0]
                            if isinstance(first_target, dict) and 'price' in first_target:
                                target_price = int(first_target['price'])

                        if 'stop_loss' in trading_plan:
                            stop_loss = trading_plan['stop_loss']
                            if isinstance(stop_loss, (int, float)) and stop_loss > 0:
                                stop_loss_price = int(stop_loss)

                    if target_price == current_price:
                        if signal == 'buy':
                            volatility = stock_data.get('volatility', 3.0)
                            target_price = int(current_price * (1 + volatility / 100 * 2))
                        else:
                            target_price = int(current_price * 1.05)

                    if stop_loss_price == current_price:
                        support_price = stock_data.get('support_price', 0)
                        if support_price > 0 and support_price < current_price:
                            stop_loss_price = int(support_price * 0.98)
                        else:
                            volatility = stock_data.get('volatility', 3.0)
                            stop_loss_price = int(current_price * (1 - volatility / 100))

                    result = {
                        'score': 0,
                        'signal': signal,
                        'split_strategy': entry_strategy,
                        'confidence': data.get('confidence_level', 'Medium'),
                        'recommendation': signal,
                        'reasons': reasons if reasons else ['AI 분석 완료'],
                        'risks': warnings if isinstance(warnings, list) else [],
                        'target_price': target_price,
                        'stop_loss_price': stop_loss_price,
                        'analysis_text': cleaned_text,
                    }

                    logger.info(f"✅ JSON 응답 파싱 성공: {signal}")
                    return result

                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 파싱 실패, 텍스트 파싱으로 전환")
                except Exception as e:
                    logger.warning(f"JSON 처리 중 예외: {type(e).__name__}: {e}, 텍스트 파싱으로 전환")

        except Exception as e:
            logger.warning(f"JSON 추출 중 예외 발생: {type(e).__name__}: {e}, 텍스트 파싱으로 전환")

        logger.info("텍스트 파싱 모드로 전환")

        text_lower = response_text.lower()
        signal = 'hold'

        if 'strong buy' in text_lower or 'strong_buy' in text_lower:
            signal = 'buy'
        elif 'buy' in text_lower and 'not' not in text_lower[:text_lower.find('buy')] if 'buy' in text_lower else False:
            signal = 'buy'
        elif 'sell' in text_lower:
            signal = 'sell'

        current_price = stock_data.get('current_price', 0)
        volatility = stock_data.get('volatility', 3.0)
        support_price = stock_data.get('support_price', 0)

        if signal == 'buy':
            target_price = int(current_price * (1 + volatility / 100 * 2))
        else:
            target_price = int(current_price * 1.05)

        if support_price > 0 and support_price < current_price:
            stop_loss_price = int(support_price * 0.98)
        else:
            stop_loss_price = int(current_price * (1 - volatility / 100))

        result = {
            'score': 0,
            'signal': signal,
            'split_strategy': '',
            'confidence': 'Medium',
            'recommendation': signal,
            'reasons': [response_text[:200] if len(response_text) > 200 else response_text],
            'risks': [],
            'target_price': target_price,
            'stop_loss_price': stop_loss_price,
            'analysis_text': response_text,
        }

        logger.info(f"텍스트 파싱 완료: {signal}")
        return result

    def _parse_market_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """시장 분석 응답 파싱"""
        result = {
            'market_sentiment': 'neutral',
            'market_score': 5.0,
            'analysis': response_text,
            'recommendations': [],
        }

        text_lower = response_text.lower()

        if 'bullish' in text_lower or '상승' in response_text:
            result['market_sentiment'] = 'bullish'
            result['market_score'] = 7.0
        elif 'bearish' in text_lower or '하락' in response_text:
            result['market_sentiment'] = 'bearish'
            result['market_score'] = 3.0

        return result

    def _parse_portfolio_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """포트폴리오 분석 응답 파싱"""
        return {
            'analysis': response_text,
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
        }

    # ==================== 유틸리티 ====================

    def _format_holdings_data(self, holdings: list) -> str:
        """보유 종목 포맷팅"""
        if not holdings:
            return "보유 종목 없음"

        text = ""
        for h in holdings[:5]:
            text += f"- {h.get('stock_name', '')}: {h.get('profit_loss_rate', 0):+.2f}%\n"

        return text

    def _get_error_result(self, error_msg: str) -> Dict[str, Any]:
        """에러 결과 반환"""
        return {
            'error': True,
            'error_message': error_msg,
            'score': 5.0,
            'signal': 'hold',
            'confidence': 'Low',
            'recommendation': '분석 실패',
            'reasons': [error_msg],
            'risks': [],
        }

    # ==================== 크로스 체크 ====================

    def _analyze_with_single_model(
        self,
        model,
        model_name: str,
        prompt: str,
        stock_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        단일 모델로 분석 수행

        Args:
            model: Gemini 모델 인스턴스
            model_name: 모델 이름 (로깅용)
            prompt: 분석 프롬프트
            stock_data: 종목 데이터

        Returns:
            분석 결과 또는 None (실패시)
        """
        try:
            logger.info(f"[{model_name}] 분석 시작")

            response = model.generate_content(
                prompt,
                request_options={'timeout': 60}
            )

            if not response.candidates:
                logger.warning(f"[{model_name}] No candidates")
                return None

            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason

            if finish_reason != 1:
                reason_map = {2: "SAFETY", 3: "MAX_TOKENS", 4: "RECITATION", 5: "OTHER"}
                reason_name = reason_map.get(finish_reason, f"UNKNOWN({finish_reason})")
                logger.warning(f"[{model_name}] Blocked: {reason_name}")
                return None

            if not hasattr(response, 'text'):
                logger.warning(f"[{model_name}] No text attribute")
                return None

            response_text = response.text
            if not response_text or len(response_text.strip()) == 0:
                logger.warning(f"[{model_name}] Empty response")
                return None

            result = self._parse_stock_analysis_response(response_text, stock_data)
            result['model_name'] = model_name
            logger.info(f"[{model_name}] 분석 완료: {result['signal']}")

            return result

        except Exception as e:
            logger.error(f"[{model_name}] 분석 실패: {e}")
            return None

    def _cross_check_results(
        self,
        result_2_0: Optional[Dict[str, Any]],
        result_2_5: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        두 모델의 결과를 크로스 체크하여 최종 결과 생성

        Args:
            result_2_0: 2.0 모델 결과
            result_2_5: 2.5 모델 결과

        Returns:
            통합 분석 결과
        """
        if not result_2_0 and not result_2_5:
            logger.error("크로스체크: 모든 모델 실패")
            return self._get_error_result("모든 모델 분석 실패")

        if not result_2_0:
            logger.warning("크로스체크: 2.0 실패, 2.5만 사용")
            result_2_5['cross_check'] = {
                'enabled': True,
                'model_2_0_failed': True,
                'model_2_5_signal': result_2_5['signal'],
                'agreement': 'N/A'
            }
            return result_2_5

        if not result_2_5:
            logger.warning("크로스체크: 2.5 실패, 2.0만 사용")
            result_2_0['cross_check'] = {
                'enabled': True,
                'model_2_0_signal': result_2_0['signal'],
                'model_2_5_failed': True,
                'agreement': 'N/A'
            }
            return result_2_0

        signal_2_0 = result_2_0['signal']
        signal_2_5 = result_2_5['signal']

        logger.info(f"크로스체크: 2.0={signal_2_0}, 2.5={signal_2_5}")

        signals_match = (signal_2_0 == signal_2_5)

        if signals_match:
            logger.info(f"✅ 크로스체크 일치: {signal_2_0}")
            final_result = result_2_5.copy()

            confidence_map = {
                'Low': 'Medium',
                'Medium': 'High',
                'High': 'Very High',
                'Very High': 'Very High'
            }
            original_confidence = final_result.get('confidence', 'Medium')
            final_result['confidence'] = confidence_map.get(original_confidence, 'High')

            final_result['cross_check'] = {
                'enabled': True,
                'model_2_0_signal': signal_2_0,
                'model_2_5_signal': signal_2_5,
                'agreement': True,
                'original_confidence': original_confidence,
                'boosted_confidence': final_result['confidence']
            }

        else:
            logger.warning(f"⚠️ 크로스체크 불일치: 2.0={signal_2_0}, 2.5={signal_2_5}")

            signal_priority = {'sell': 0, 'hold': 1, 'buy': 2}
            priority_2_0 = signal_priority.get(signal_2_0, 1)
            priority_2_5 = signal_priority.get(signal_2_5, 1)

            if 'hold' in [signal_2_0, signal_2_5]:
                final_signal = 'hold'
                chosen_model = '보수적 선택'
            elif priority_2_0 < priority_2_5:
                final_signal = signal_2_0
                chosen_model = '2.0'
            else:
                final_signal = signal_2_5
                chosen_model = '2.5'

            logger.info(f"최종 신호: {final_signal} (선택: {chosen_model})")

            final_result = result_2_5.copy()
            final_result['signal'] = final_signal
            final_result['recommendation'] = final_signal
            final_result['confidence'] = 'Medium'

            reasons_combined = []
            if result_2_0.get('reasons'):
                reasons_combined.append(f"[2.0] " + "; ".join(result_2_0['reasons'][:2]))
            if result_2_5.get('reasons'):
                reasons_combined.append(f"[2.5] " + "; ".join(result_2_5['reasons'][:2]))
            final_result['reasons'] = reasons_combined

            final_result['cross_check'] = {
                'enabled': True,
                'model_2_0_signal': signal_2_0,
                'model_2_5_signal': signal_2_5,
                'agreement': False,
                'final_signal': final_signal,
                'reason': f'불일치로 보수적 선택 ({chosen_model})'
            }

        return final_result


__all__ = ['GeminiAnalyzer']
