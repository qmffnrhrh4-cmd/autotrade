"""
config/api_loader.py
검증된 API 사양 로더

_immutable/api_specs/ 폴더의 검증된 API 목록을 로드하고 제공합니다.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache

# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
API_SPECS_DIR = PROJECT_ROOT / '_immutable' / 'api_specs'
SUCCESSFUL_APIS_FILE = API_SPECS_DIR / 'successful_apis.json'
APIS_BY_CATEGORY_FILE = API_SPECS_DIR / 'apis_by_category.json'


class APILoader:
    """검증된 API 사양 로더 (자동 리로드 지원)"""

    def __init__(self):
        self._successful_apis: Optional[Dict] = None
        self._apis_by_category: Optional[Dict] = None
        self._file_mtime: Optional[float] = None  # 파일 수정 시간 추적
        self._load_apis()

    def _check_and_reload(self):
        """파일이 변경되었으면 자동 리로드"""
        try:
            if SUCCESSFUL_APIS_FILE.exists():
                current_mtime = os.path.getmtime(SUCCESSFUL_APIS_FILE)
                if self._file_mtime is None or current_mtime > self._file_mtime:
                    # 파일이 변경됨 - 리로드
                    self._load_apis()
        except Exception:
            pass  # 파일 체크 실패시 무시

    def _load_apis(self):
        """API 사양 파일 로드"""
        try:
            # successful_apis.json 로드
            if SUCCESSFUL_APIS_FILE.exists():
                with open(SUCCESSFUL_APIS_FILE, 'r', encoding='utf-8') as f:
                    self._successful_apis = json.load(f)
                # 파일 수정 시간 저장
                self._file_mtime = os.path.getmtime(SUCCESSFUL_APIS_FILE)
            else:
                raise FileNotFoundError(
                    f"API 사양 파일을 찾을 수 없습니다: {SUCCESSFUL_APIS_FILE}\n"
                    "먼저 API 테스트를 실행하여 성공한 API 목록을 생성하세요."
                )

            # apis_by_category.json 로드
            if APIS_BY_CATEGORY_FILE.exists():
                with open(APIS_BY_CATEGORY_FILE, 'r', encoding='utf-8') as f:
                    self._apis_by_category = json.load(f)

        except json.JSONDecodeError as e:
            raise ValueError(f"API 사양 파일 파싱 오류: {e}")
        except Exception as e:
            raise RuntimeError(f"API 사양 로드 실패: {e}")

    def get_all_apis(self) -> Dict[str, Any]:
        """모든 성공한 API 반환"""
        self._check_and_reload()  # 파일 변경 확인 및 자동 리로드
        if self._successful_apis is None:
            self._load_apis()
        return self._successful_apis.get('apis', {})

    def get_api(self, api_id: str) -> Optional[Dict[str, Any]]:
        """특정 API 정보 반환"""
        apis = self.get_all_apis()
        return apis.get(api_id)

    def get_apis_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리별 API 목록 반환"""
        if self._apis_by_category is None:
            self._load_apis()

        categories = self._apis_by_category.get('categories', {})
        return categories.get(category, [])

    def get_all_categories(self) -> List[str]:
        """모든 카테고리 목록 반환"""
        if self._apis_by_category is None:
            self._load_apis()

        categories = self._apis_by_category.get('categories', {})
        return sorted(categories.keys())

    def get_api_call(self, api_id: str, variant_idx: int = 1) -> Optional[Dict[str, Any]]:
        """특정 API의 특정 variant 호출 정보 반환"""
        api = self.get_api(api_id)
        if not api:
            return None

        calls = api.get('calls', [])
        for call in calls:
            if call.get('variant_idx') == variant_idx:
                return call

        # variant_idx가 없으면 첫 번째 호출 반환
        return calls[0] if calls else None

    def get_metadata(self) -> Dict[str, Any]:
        """API 사양 메타데이터 반환"""
        if self._successful_apis is None:
            self._load_apis()
        return self._successful_apis.get('metadata', {})

    def get_stats(self) -> Dict[str, Any]:
        """API 통계 반환"""
        metadata = self.get_metadata()
        return metadata.get('stats', {})

    def search_apis(self, keyword: str) -> List[Dict[str, Any]]:
        """API 이름으로 검색"""
        apis = self.get_all_apis()
        results = []

        keyword_lower = keyword.lower()
        for api_id, api_info in apis.items():
            api_name = api_info.get('api_name', '').lower()
            if keyword_lower in api_name or keyword_lower in api_id.lower():
                results.append({
                    'api_id': api_id,
                    **api_info
                })

        return results

    def is_api_available(self, api_id: str) -> bool:
        """API 사용 가능 여부 확인"""
        self._check_and_reload()  # 파일 변경 확인 및 자동 리로드
        return self.get_api(api_id) is not None

    def get_account_apis(self) -> List[Dict[str, Any]]:
        """계좌 관련 API 목록"""
        return self.get_apis_by_category('account')

    def get_market_apis(self) -> List[Dict[str, Any]]:
        """시세 관련 API 목록"""
        return self.get_apis_by_category('market')

    def get_ranking_apis(self) -> List[Dict[str, Any]]:
        """순위 관련 API 목록"""
        return self.get_apis_by_category('ranking')

    def get_search_apis(self) -> List[Dict[str, Any]]:
        """검색 관련 API 목록"""
        return self.get_apis_by_category('search')


# 싱글톤 인스턴스
_api_loader_instance: Optional[APILoader] = None


@lru_cache(maxsize=1)
def get_api_loader() -> APILoader:
    """API 로더 싱글톤 인스턴스 반환"""
    global _api_loader_instance
    if _api_loader_instance is None:
        _api_loader_instance = APILoader()
    return _api_loader_instance


# 편의 함수들
def load_successful_apis() -> Dict[str, Any]:
    """성공한 모든 API 로드"""
    return get_api_loader().get_all_apis()


def get_api_by_id(api_id: str) -> Optional[Dict[str, Any]]:
    """API ID로 조회"""
    return get_api_loader().get_api(api_id)


def get_api_by_category(category: str) -> List[Dict[str, Any]]:
    """카테고리별 API 목록"""
    return get_api_loader().get_apis_by_category(category)


def search_api(keyword: str) -> List[Dict[str, Any]]:
    """API 검색"""
    return get_api_loader().search_apis(keyword)


def is_api_tested(api_id: str) -> bool:
    """API가 테스트되었는지 확인"""
    return get_api_loader().is_api_available(api_id)


# 카테고리 상수
class APICategory:
    """API 카테고리 상수"""
    ACCOUNT = 'account'
    MARKET = 'market'
    RANKING = 'ranking'
    SEARCH = 'search'
    INFO = 'info'
    ELW = 'elw'
    FUTURES = 'futures'
    OTHER = 'other'


__all__ = [
    'APILoader',
    'get_api_loader',
    'load_successful_apis',
    'get_api_by_id',
    'get_api_by_category',
    'search_api',
    'is_api_tested',
    'APICategory',
]
