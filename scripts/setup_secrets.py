#!/usr/bin/env python3
"""
setup_secrets.py
API 키 및 민감정보 안전 설정 스크립트

이 스크립트는:
1. 사용자로부터 API 키를 안전하게 입력받습니다 (복사 붙여넣기 가능)
2. _immutable/credentials/secrets.json 파일을 생성합니다
3. 파일을 읽기 전용(400)으로 설정하여 실수로 수정되지 않도록 보호합니다
"""

import json
import os
import sys
from pathlib import Path

# 색상 코드
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent  # scripts 디렉토리의 상위 디렉토리
SECRETS_DIR = PROJECT_ROOT / '_immutable' / 'credentials'
SECRETS_FILE = SECRETS_DIR / 'secrets.json'
EXAMPLE_FILE = SECRETS_DIR / 'secrets.example.json'


def print_header():
    """헤더 출력"""
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}🔐 API 키 안전 설정 스크립트{RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")


def check_existing_file():
    """기존 파일 확인"""
    if SECRETS_FILE.exists():
        print(f"{YELLOW}⚠️  secrets.json 파일이 이미 존재합니다.{RESET}")
        response = input(f"{YELLOW}덮어쓰시겠습니까? (yes/no): {RESET}").strip().lower()

        if response not in ['yes', 'y']:
            print(f"{RED}❌ 설정을 취소했습니다.{RESET}")
            sys.exit(0)

        # 기존 파일 권한 변경 (쓰기 가능하게)
        try:
            os.chmod(SECRETS_FILE, 0o600)
            print(f"{GREEN}✅ 기존 파일을 덮어쓸 수 있도록 권한을 변경했습니다.{RESET}\n")
        except Exception as e:
            print(f"{RED}❌ 권한 변경 실패: {e}{RESET}")
            print(f"{YELLOW}💡 수동으로 실행하세요: chmod 600 {SECRETS_FILE}{RESET}")
            sys.exit(1)


def input_with_default(prompt, default="", required=True, mask=False):
    """기본값이 있는 입력 받기"""
    default_display = f" [{default}]" if default else ""
    required_mark = " (필수)" if required else " (선택)"

    # mask는 표시만 하지 않고, 복사 붙여넣기는 허용
    if mask:
        print(f"{YELLOW}💡 보안 정보입니다. 복사 붙여넣기를 사용하세요.{RESET}")

    while True:
        value = input(f"{prompt}{default_display}{required_mark}: ").strip()

        if not value:
            value = default

        if required and not value:
            print(f"{RED}❌ 필수 항목입니다. 값을 입력해주세요.{RESET}")
            continue

        return value


def collect_credentials():
    """사용자로부터 자격증명 수집"""
    print(f"{BOLD}1️⃣  키움증권 REST API 설정{RESET}")
    print(f"{YELLOW}   (키움증권 Open API 앱키/시크릿키){RESET}\n")

    kiwoom_rest = {
        "base_url": input_with_default(
            "REST API URL",
            default="https://api.kiwoom.com",
            required=True,
            mask=False
        ),
        "appkey": input_with_default(
            "앱키 (App Key)",
            required=True,
            mask=True
        ),
        "secretkey": input_with_default(
            "시크릿키 (Secret Key)",
            required=True,
            mask=True
        ),
        "account_number": input_with_default(
            "계좌번호 (형식: 12345678-01)",
            required=True,
            mask=False
        )
    }

    print(f"\n{BOLD}2️⃣  키움증권 WebSocket 설정{RESET}\n")
    kiwoom_websocket = {
        "url": input_with_default(
            "WebSocket URL",
            default="wss://api.kiwoom.com:10000/api/dostk/websocket",
            required=True,
            mask=False
        )
    }

    print(f"\n{BOLD}3️⃣  Google Gemini API 설정{RESET}\n")
    gemini = {
        "api_key": input_with_default(
            "Gemini API Key",
            required=True,
            mask=True
        ),
        "model_name": input_with_default(
            "모델명",
            default="gemini-2.5-flash",
            required=True,
            mask=False
        )
    }

    print(f"\n{BOLD}4️⃣  Telegram Bot 설정{RESET}")
    print(f"{YELLOW}   (선택사항 - 알림을 받으려면 입력하세요){RESET}\n")
    telegram = {
        "bot_token": input_with_default(
            "Bot Token",
            required=False,
            mask=True
        ),
        "chat_id": input_with_default(
            "Chat ID",
            required=False,
            mask=False
        )
    }

    return {
        "_comment": "이 파일은 절대 git에 커밋하지 마세요!",
        "_warning": "파일이 읽기 전용으로 설정되어 있습니다. 수정이 필요하면 setup_secrets.py를 다시 실행하세요.",
        "kiwoom_rest": kiwoom_rest,
        "kiwoom_websocket": kiwoom_websocket,
        "gemini": gemini,
        "telegram": telegram
    }


def save_secrets(secrets):
    """secrets.json 저장 및 보호"""
    try:
        # 디렉토리 생성 (이미 존재하면 무시)
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)

        # JSON 파일 저장
        with open(SECRETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(secrets, f, indent=2, ensure_ascii=False)

        print(f"\n{GREEN}✅ secrets.json 파일이 생성되었습니다.{RESET}")
        print(f"{BLUE}📁 위치: {SECRETS_FILE}{RESET}")

        # 파일 권한을 읽기 전용(400)으로 설정
        os.chmod(SECRETS_FILE, 0o400)
        print(f"{GREEN}🔒 파일이 읽기 전용으로 보호되었습니다 (chmod 400).{RESET}")

        return True

    except Exception as e:
        print(f"{RED}❌ 파일 저장 실패: {e}{RESET}")
        return False


def verify_secrets():
    """저장된 secrets.json 검증"""
    try:
        with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
            secrets = json.load(f)

        print(f"\n{BOLD}{GREEN}{'='*80}{RESET}")
        print(f"{BOLD}{GREEN}✅ 설정 완료!{RESET}")
        print(f"{BOLD}{GREEN}{'='*80}{RESET}\n")

        # 설정된 항목 요약
        kiwoom = secrets.get('kiwoom_rest', {})
        gemini = secrets.get('gemini', {})
        telegram = secrets.get('telegram', {})

        print(f"{BOLD}설정 요약:{RESET}")
        print(f"  • 키움 REST API: {BLUE}{kiwoom.get('base_url', 'N/A')}{RESET}")
        print(f"  • 계좌번호: {BLUE}{kiwoom.get('account_number', 'N/A')}{RESET}")
        print(f"  • Gemini 모델: {BLUE}{gemini.get('model_name', 'N/A')}{RESET}")

        if telegram.get('bot_token'):
            print(f"  • Telegram: {GREEN}설정됨{RESET}")
        else:
            print(f"  • Telegram: {YELLOW}미설정{RESET}")

        print(f"\n{BOLD}{BLUE}중요 안내:{RESET}")
        print(f"  1. 이 파일은 {RED}절대 git에 커밋하지 마세요{RESET}")
        print(f"  2. 파일은 읽기 전용으로 보호되어 있습니다")
        print(f"  3. 수정이 필요하면: {YELLOW}python setup_secrets.py{RESET} 다시 실행")
        print(f"  4. 수동으로 수정하려면: {YELLOW}chmod 600 {SECRETS_FILE}{RESET} 먼저 실행\n")

        return True

    except Exception as e:
        print(f"{RED}❌ 검증 실패: {e}{RESET}")
        return False


def main():
    """메인 함수"""
    try:
        print_header()

        # 기존 파일 확인
        check_existing_file()

        # 자격증명 수집
        print(f"{BOLD}{BLUE}API 키를 입력해주세요:{RESET}\n")
        print(f"{YELLOW}💡 복사 붙여넣기를 사용하세요 (Ctrl+V 또는 Cmd+V).{RESET}\n")

        secrets = collect_credentials()

        # 확인
        print(f"\n{BOLD}{YELLOW}{'='*80}{RESET}")
        print(f"{BOLD}{YELLOW}⚠️  입력한 정보를 확인하세요{RESET}")
        print(f"{BOLD}{YELLOW}{'='*80}{RESET}\n")

        response = input(f"{YELLOW}설정을 저장하시겠습니까? (yes/no): {RESET}").strip().lower()

        if response not in ['yes', 'y']:
            print(f"{RED}❌ 설정을 취소했습니다.{RESET}")
            sys.exit(0)

        # 저장 및 보호
        if save_secrets(secrets):
            verify_secrets()
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n{RED}❌ 사용자가 취소했습니다.{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}❌ 오류 발생: {e}{RESET}")
        sys.exit(1)


if __name__ == '__main__':
    main()
