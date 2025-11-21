# Quick Start Guide - Database & Dashboard

## Prerequisites Check
✅ Data directory created: `/home/user/autotrade/data/`
✅ Database files initialized:
  - `virtual_trading.db` (53,248 bytes)
  - `strategy_evolution.db` (36,864 bytes)

## Quick Commands

### 1. Initialize Databases (First Time Setup)
```bash
python scripts/init_databases.py
```

### 2. Verify Database Health
```bash
python scripts/verify_databases.py
```

### 3. Test Dashboard Integration
```bash
python scripts/test_dashboard_integration.py
```

### 4. Start Dashboard
```bash
python main.py --dashboard
```
Then open: http://localhost:5000

## Dashboard Pages

### Main Pages
- **Home**: http://localhost:5000/
- **Settings**: http://localhost:5000/settings
- **Backtest**: http://localhost:5000/backtest
- **Chart**: http://localhost:5000/chart
- **Evolution**: http://localhost:5000/evolution (NEW!)

### API Endpoints

#### Virtual Trading
```bash
# List all strategies
curl http://localhost:5000/api/virtual-trading/strategies

# Create strategy
curl -X POST http://localhost:5000/api/virtual-trading/strategies \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Strategy","description":"My test","initial_capital":1000000}'

# Get positions
curl http://localhost:5000/api/virtual-trading/positions

# Get trades
curl http://localhost:5000/api/virtual-trading/trades
```

#### Strategy Evolution
```bash
# Current status
curl http://localhost:5000/api/evolution/status

# Evolution history
curl http://localhost:5000/api/evolution/history

# Best strategy
curl http://localhost:5000/api/evolution/best-strategy

# Deployment status
curl http://localhost:5000/api/evolution/deployment-status
```

## Testing Workflow

### 1. Test Virtual Trading
```bash
# Create a test strategy
curl -X POST http://localhost:5000/api/virtual-trading/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Strategy",
    "description": "Testing virtual trading",
    "initial_capital": 10000000
  }'

# List strategies to verify
curl http://localhost:5000/api/virtual-trading/strategies

# Simulate a buy order
curl -X POST http://localhost:5000/api/virtual-trading/buy \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": 1,
    "stock_code": "005930",
    "stock_name": "Samsung Electronics",
    "quantity": 10,
    "price": 70000
  }'

# Check positions
curl http://localhost:5000/api/virtual-trading/positions
```

### 2. Test Evolution System
```bash
# Check if evolution is running
curl http://localhost:5000/api/evolution/status

# If not running, start evolution engine:
python run_strategy_optimizer.py --auto-deploy

# Check history after some time
curl http://localhost:5000/api/evolution/history
```

## Common Issues & Solutions

### Issue: Database file not found
**Solution:**
```bash
python scripts/init_databases.py
```

### Issue: Permission denied on data directory
**Solution:**
```bash
sudo chown -R $USER:$USER /home/user/autotrade/data/
chmod 755 /home/user/autotrade/data/
```

### Issue: Dashboard won't start
**Solution:**
```bash
# Check if port 5000 is already in use
lsof -i :5000

# If in use, stop the process or use a different port:
python main.py --dashboard --port 5001
```

### Issue: Routes return 404
**Solution:**
Verify routes are registered in `/home/user/autotrade/dashboard/app.py`:
```bash
grep "register_blueprint" dashboard/app.py
```

## Database Schema Quick Reference

### virtual_trading.db

#### virtual_strategies
```sql
SELECT * FROM virtual_strategies;
-- Columns: id, name, description, initial_capital, current_capital,
--          total_profit, return_rate, win_rate, trade_count, etc.
```

#### virtual_positions
```sql
SELECT * FROM virtual_positions WHERE is_closed = 0;
-- Active positions only
```

#### virtual_trades
```sql
SELECT * FROM virtual_trades
ORDER BY timestamp DESC
LIMIT 10;
-- Recent trades
```

### strategy_evolution.db

#### evolved_strategies
```sql
SELECT generation, COUNT(*) as strategies
FROM evolved_strategies
GROUP BY generation
ORDER BY generation DESC;
-- Strategies per generation
```

#### fitness_results
```sql
SELECT * FROM fitness_results
ORDER BY fitness_score DESC
LIMIT 10;
-- Top 10 strategies
```

#### generation_stats
```sql
SELECT * FROM generation_stats
ORDER BY generation DESC;
-- Generation statistics
```

## Performance Tips

### Database Optimization
- Databases use WAL mode for better concurrency
- Indexes are optimized for common queries
- Regular VACUUM recommended for SQLite maintenance

### Dashboard Performance
- Use WebSocket connections for real-time data
- Enable caching in production
- Monitor memory usage during evolution

## Monitoring Commands

### Check Database Size
```bash
du -sh /home/user/autotrade/data/*.db
```

### Check Table Row Counts
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/virtual_trading.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM virtual_strategies')
print(f'Strategies: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM virtual_positions')
print(f'Positions: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM virtual_trades')
print(f'Trades: {cursor.fetchone()[0]}')
"
```

### Check Evolution Progress
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/strategy_evolution.db')
cursor = conn.cursor()
cursor.execute('SELECT MAX(generation) FROM generation_stats')
max_gen = cursor.fetchone()[0]
print(f'Latest Generation: {max_gen if max_gen else 0}')
"
```

## Next Steps

1. **Start the Dashboard**
   ```bash
   python main.py --dashboard
   ```

2. **Create Your First Virtual Strategy**
   - Visit http://localhost:5000/evolution
   - Use the API or web interface

3. **Start Evolution Engine** (Optional)
   ```bash
   python run_strategy_optimizer.py --auto-deploy
   ```

4. **Monitor Performance**
   - Check `/api/evolution/status` regularly
   - Review strategy performance metrics

## Support
- Database issues: See `DATABASE_INITIALIZATION_SUMMARY.md`
- Route issues: Check `dashboard/routes/` directory
- Evolution issues: See `virtual_trading/evolution_engine.py`

---
**Ready to Trade!** 🚀
All systems are initialized and ready for virtual trading and strategy evolution.
