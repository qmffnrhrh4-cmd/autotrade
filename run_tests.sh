#!/bin/bash
# 진화 알고리즘 시스템 테스트 메뉴

while true; do
    clear
    echo "========================================"
    echo " 진화 알고리즘 시스템 테스트 메뉴"
    echo "========================================"
    echo
    echo "  [1] 간단 테스트 (파일구조, 스레드, 지표)"
    echo "  [2] 전체 테스트 (진화엔진 상세)"
    echo "  [3] 모두 실행"
    echo "  [0] 종료"
    echo
    echo "========================================"
    read -p "선택: " choice

    case $choice in
        1)
            clear
            echo "========================================"
            echo " 간단 테스트 실행 중..."
            echo "========================================"
            echo
            python3 tests/test_simple_evolution.py
            echo
            read -p "계속하려면 Enter를 누르세요..."
            ;;
        2)
            clear
            echo "========================================"
            echo " 전체 테스트 실행 중..."
            echo "========================================"
            echo
            python3 tests/test_evolution_engine.py
            echo
            read -p "계속하려면 Enter를 누르세요..."
            ;;
        3)
            clear
            echo "========================================"
            echo " 모든 테스트 실행 중..."
            echo "========================================"
            echo
            echo "[1/2] 간단 테스트..."
            python3 tests/test_simple_evolution.py
            echo
            echo "----------------------------------------"
            echo
            echo "[2/2] 전체 테스트..."
            python3 tests/test_evolution_engine.py
            echo
            echo "========================================"
            echo " 모든 테스트 완료!"
            echo "========================================"
            read -p "계속하려면 Enter를 누르세요..."
            ;;
        0)
            echo "종료합니다."
            exit 0
            ;;
        *)
            echo "잘못된 선택입니다."
            sleep 1
            ;;
    esac
done
