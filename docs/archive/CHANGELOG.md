# AutoTrade Pro - Changelog

All notable changes to AutoTrade Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [5.7.4] - 2025-11-05

### 🚀 Major Dashboard Upgrade: 10 Diverse Trading Strategies

#### Changed
- **Dashboard Virtual Trading Display**: Upgraded from 3 hardcoded strategies to dynamic 10-strategy display
  - Now shows all 10 diverse strategies: 모멘텀추세, 평균회귀, 돌파매매, 가치투자, 스윙매매, MACD크로스, 역발상, 섹터순환, 급등추격, 배당성장
  - Each strategy has unique icon and color coding
  - Real-time strategy performance tracking
- **Color Convention**: Changed to Korean stock market standard
  - Profit = Red (#ef4444) - 이익은 빨간색
  - Loss = Blue (#3b82f6) - 손실은 파란색
  - Applied consistently across all dashboard components
- **Number Animations**: Enhanced smooth animations
  - Strategy card metrics animate on update
  - Consistent easeOutCubic animation across all numeric displays
  - Assets, returns, positions all use smooth transitions

#### Fixed
- **AI Analysis Robustness**: Never returns None
  - Sentiment analysis always returns data (even on error)
  - Risk analysis always returns data (even on error)
  - Portfolio analysis has proper fallback values
  - Graceful degradation with meaningful status messages

#### Added
- **Dynamic Strategy Cards**: JavaScript generates 10 cards from API data
  - First render: Full HTML generation
  - Updates: Smooth numeric transitions without DOM recreation
  - Individual strategy detail view on click

### 📊 Technical Details
```
Dashboard Changes:
- updateVirtualStrategies(): Now handles 10 strategies dynamically
- toggleStrategyDetails(): Updated to work with all 10 strategies
- Color scheme: Red/Blue instead of Green/Red
- Smooth animations: Applied to strategy metrics

AI Analysis:
- Sentiment: Always returns {overall_score, status, count, analyzed_stocks}
- Risk: Always returns {risk_level, risk_score, max_weight, diversification}
- Portfolio: Always returns {score, health, recommendations}
- Error handling: Fallback to neutral values on failure
```

---

## [5.6.0] - 2025-11-05

### 🎯 UX Improvements & Optimization

#### Fixed
- **Dashboard Virtual Trading Refresh Issue**: Fixed unreadable trading history due to auto-refresh every 3s
  - Added manual refresh button
  - Added JSON download button
  - Added auto-refresh toggle checkbox (opt-in)
  - Virtual trades no longer refresh automatically, improving readability

#### Changed
- **Dashboard Version**: Updated to v5.6.0
- **Dashboard Header**: Improved logo and version display
- **Code Cleanup**: Removed 7 verbose DEBUG log statements
  - dashboard/routes/account.py: Removed after-hours calculation verbose log
  - dashboard/routes/system.py: Silenced optional Gemini connection errors
  - main.py: Cleaned up 5 DEBUG prints in test trade function

#### Added
- **Documentation**: Created CHANGELOG.md (consolidated from multiple version files)
- **Documentation**: Maintained OPTIMIZATION_NOTES_v5.5.md for future work

### 📊 Impact
- Improved UX: Virtual trades now readable
- Cleaner console output: -7 DEBUG logs
- Better documentation structure

---

## [5.5.1] - 2025-11-05

### 🧹 Project Cleanup & Optimization

#### Removed
- **Obsolete Code**: Deleted dashboard/app_apple.py (3,249 lines, ~100KB)
  - Replaced by modular dashboard/app.py in v5.4.0
  - No longer used in production

#### Changed
- **Deployment Scripts**: Updated restart_fix.sh
  - Removed app_apple.py references
  - Simplified to manage only main.py (dashboard auto-starts)
  - Updated instructions and documentation

#### Added
- **Documentation**: OPTIMIZATION_NOTES_v5.5.md
  - Comprehensive optimization guide
  - Documents completed work and future recommendations
  - Prioritized optimizations with estimated impact

### 📊 Impact
- Code reduction: -3,249 lines
- Simplified deployment
- Better documentation for future work
- Potential future reduction: 2,300+ lines of complexity documented

---

## [5.5.0] - 2025-11-05

### 🐛 Critical Bug Fix

#### Fixed
- **Account Balance 2x Duplication Bug** (CRITICAL)
  - Problem: Dashboard showed 1,899,712원 instead of 952,895원 (mobile truth)
  - Root Cause: Separate KRX+NXT queries returned same stocks twice
  - Solution: Use API's unified `market_type="KRX+NXT"` parameter
  - Result: 952,912원 (matches mobile 952,895원 with 99.98% accuracy)
  - Error margin: ~17원 (likely rounding/fees)

#### Changed
- **dashboard/routes/account.py**: 3 functions fixed
  - `get_account()`: Unified KRX+NXT query
  - `get_positions()`: Unified KRX+NXT query
  - `get_real_holdings()`: Unified KRX+NXT query
  - Improved logging: [ACCOUNT] tags instead of verbose [DEBUG]

- **tests/integration/test_account_balance.py**: Updated to use unified query
  - Preserved after-hours eval_amt=0 handling

- **tests/integration/test_nxt_current_price.py**: Updated to use unified query
  - Preserved after-hours calculation logic

### 📊 Technical Details
```
OLD: holdings_krx + holdings_nxt → Same stocks appeared twice
NEW: holdings(market_type="KRX+NXT") → Each stock counted once

API already supported unified query via variant_idx=3
```

---

## [5.4.2] - 2025-11-04

### Fixed
- **Dashboard Import Error**: Fixed "No module named 'routes'"
  - Changed absolute imports to relative imports
  - `from routes import` → `from .routes import`
  - `from websocket import` → `from .websocket import`

- **Account Balance Calculation**: Fixed after-hours balance calculation
  - When `eval_amt=0`, manually calculate `quantity × cur_prc`
  - Ensures accurate balance 24/7, not just during market hours

---

## [5.4.1] - 2025-11-04

### 🧹 Comprehensive Project Cleanup

#### Removed
- **18 obsolete files** (~1.4MB total)
  - Backups: app_apple_backup_v5.3.3.py, various .bak files
  - Generated reports: 6 test result files, analysis outputs
  - Duplicate configurations: multiple settings files

#### Reorganized
- **50+ files** moved to proper locations
  - 16 root test scripts → tests/manual/
  - 6 guides → docs/guides/
  - 12 temp fixes → docs/archive/temp_fixes/
  - 5 V4.x docs → docs/archive/versions/v4/
  - Multiple reports → docs/archive/

#### Changed
- **Root directory**: 94% reduction (17 Python files → 1: main.py)
- **Documentation**: Created docs/README.md for navigation

#### Fixed
- **Cross-Platform Test Imports**: Fixed Windows import errors
  - Tests now work on both Windows and Linux
  - Corrected path calculation with 3 dirname calls

### 📊 Impact
- Codebase reduction: -1.4MB
- Root files: -94% (17 → 1 Python file)
- Clear documentation hierarchy
- Better project organization

---

## [5.4.0] - 2025-11-04

### 🎯 Major Architectural Improvement: Modular Dashboard

#### Changed
- **Dashboard Architecture**: Split monolithic file into modular structure
  - Before: 1 file (3,249 lines)
  - After: 15 modular files
  - Main app: 210 lines (93% reduction)

#### New Dashboard Structure
```
dashboard/
├── app.py                  # Main app (210 lines) ⬇️ 93%
├── __init__.py             # Module exports
├── routes/                 # API endpoints (7 modules)
│   ├── account.py          # 3 endpoints
│   ├── trading.py          # 15 endpoints
│   ├── ai.py               # 25 endpoints
│   ├── market.py           # 10 endpoints
│   ├── portfolio.py        # 5 endpoints
│   ├── system.py           # 23 endpoints
│   └── pages.py            # 7 pages
├── websocket/              # Real-time updates
│   ├── __init__.py
│   └── handlers.py
└── utils/                  # Helper functions
    ├── __init__.py
    ├── validation.py
    └── response.py
```

#### Features Preserved
- ✅ All 84 endpoints functional
- ✅ All dashboard pages working
- ✅ WebSocket real-time updates
- ✅ Zero feature loss

#### Benefits
- Improved maintainability
- Easier testing (mock individual modules)
- Better code organization
- Faster navigation
- Team collaboration ready

---

## Migration Guide

### From v5.5.x to v5.6.0
No breaking changes. Dashboard UX improvements are transparent to users.

### From v5.4.x to v5.5.x
1. Delete obsolete `dashboard/app_apple.py` if manually created
2. Use updated `restart_fix.sh` for deployment
3. Review `OPTIMIZATION_NOTES_v5.5.md` for future optimization opportunities

### From v5.3.x to v5.4.x
1. Update imports if directly importing from dashboard:
   ```python
   # Before
   from dashboard.app_apple import some_function

   # After
   from dashboard.routes.account import some_function
   ```

2. Run tests to verify functionality:
   ```bash
   python tests/integration/test_account_balance.py
   ```

---

## Future Work

See `OPTIMIZATION_NOTES_v5.5.md` for detailed future optimization opportunities:

### High Priority
- Split `api/market.py` (1,899 lines → 6 modules)
  - Potential reduction: -1,200 lines complexity

### Medium Priority
- Split `main.py` (1,617 lines → 6 modules)
  - Potential reduction: -1,100 lines complexity
- Standardize logging (print → logger)
  - 60 files with print() statements

### Low Priority
- Organize test files (consolidate manual tests)
- Consolidate configuration files

**Total Potential Future Reduction**: 2,300+ lines of complexity

---

## Version History Summary

| Version | Date | Type | Description |
|---------|------|------|-------------|
| 5.6.0 | 2025-11-05 | UX/Optimization | Virtual trades fix, dashboard improvements, cleanup |
| 5.5.1 | 2025-11-05 | Cleanup | Removed obsolete app_apple.py (3,249 lines) |
| 5.5.0 | 2025-11-05 | Bug Fix | Critical account balance 2x duplication fix |
| 5.4.2 | 2025-11-04 | Bug Fix | Dashboard import errors, after-hours balance |
| 5.4.1 | 2025-11-04 | Cleanup | Project reorganization (-1.4MB, 50+ files moved) |
| 5.4.0 | 2025-11-04 | Architecture | Modular dashboard (3,249 → 210 lines) |

---

## Contributing

When adding new changes:
1. Update this CHANGELOG.md
2. Follow [Conventional Commits](https://www.conventionalcommits.org/)
3. Test all changes before committing
4. Document breaking changes in Migration Guide

---

## License

Copyright © 2025 AutoTrade Pro. All rights reserved.
