#!/bin/bash
# OpenAPI 데이터 수집 자동 실행 스크립트
# ⚠️ 주의: Kiwoom OpenAPI는 Windows에서만 작동합니다.

echo "================================================================================"
echo "  OpenAPI 데이터 수집 테스트 자동 실행"
echo "================================================================================"
echo ""

# kiwoom32 환경 확인
echo "🔧 kiwoom32 환경 확인 중..."

# conda 환경 활성화 (Anaconda Prompt에서 실행 시)
if command -v conda &> /dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate kiwoom32

    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ kiwoom32 환경 활성화 실패"
        echo "💡 먼저 conda 환경을 설정하세요:"
        echo "   conda create -n kiwoom32 python=3.8 -y"
        echo "   conda activate kiwoom32"
        echo "   pip install breadum-kiwoom pyqt5"
        exit 1
    fi

    echo "✅ kiwoom32 환경 활성화 성공"
else
    echo "⚠️  conda가 설치되어 있지 않습니다."
    echo "   Python 가상환경이 활성화되어 있다고 가정합니다."
fi

echo ""

# 사용자 선택
echo "실행할 테스트를 선택하세요:"
echo ""
echo "  1. 간단한 테스트 (4가지 데이터, 약 30초)"
echo "  2. 종합 테스트 (20가지 데이터, 약 1-2분) [권장]"
echo "  3. 기본 정보만 (로그인 + 마스터 정보, 약 10초)"
echo ""
read -p "선택 (1/2/3, 기본값=2): " choice
choice=${choice:-2}

echo ""

case $choice in
    1)
        echo "🚀 간단한 테스트 실행 중..."
        python test_stock_simple.py
        ;;
    2)
        echo "🚀 종합 테스트 실행 중..."
        python test_stock_comprehensive_20.py
        ;;
    3)
        echo "🚀 기본 정보 테스트 실행 중..."
        python test_kiwoom_direct.py
        ;;
    *)
        echo "⚠️  잘못된 선택입니다. 기본값(2번)으로 실행합니다."
        echo ""
        echo "🚀 종합 테스트 실행 중..."
        python test_stock_comprehensive_20.py
        ;;
esac

echo ""
echo "================================================================================"
echo "  테스트 완료"
echo "================================================================================"
echo ""

# 결과 검증
echo "🔍 수집된 데이터 검증 중..."
python verify_openapi_data.py

echo ""
echo "✅ 모든 작업 완료!"
echo ""
echo "📁 결과 파일 위치: tests/ 폴더"
echo ""
