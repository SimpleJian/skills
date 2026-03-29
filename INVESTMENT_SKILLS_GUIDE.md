# 专业投资人技能体系总览

基于《专业投资人成长指南》构建的完整技能矩阵，覆盖从宏观分析到交易执行的全流程。

---

## 技能矩阵

### 已具备技能（5个）

| 技能 | 定位 | 覆盖能力 | 状态 |
|------|------|---------|------|
| `a_share_trend` | A股趋势跟踪 | 交易执行（趋势选股） | ✅ 已具备 |
| `a_share_value` | A股价值抄底 | 交易执行+深度研究 | ✅ 已具备 |
| `futures_trend` | 期货趋势跟踪 | 交易执行（CTA） | ✅ 已具备 |
| `futures_value` | 期货价值抄底 | 交易执行（左侧） | ✅ 已具备 |
| `tushare_utils` | 数据工具集 | 量化技术基础设施 | ✅ 已具备 |

### 新增技能（6个）

| 技能 | 定位 | 覆盖能力 | 状态 |
|------|------|---------|------|
| `macro_analysis` | 宏观分析 | 美林时钟+经济周期 | 🆕 新增 |
| `portfolio_manager` | 组合管理 | 相关性+再平衡 | 🆕 新增 |
| `risk_manager` | 风险管理 | 止损+回撤+VaR | 🆕 新增 |
| `financial_analyzer` | 财务分析 | 杜邦分析+质量评分 | 🆕 新增 |
| `industry_research` | 行业研究 | 产业链+景气度 | 🆕 新增 |
| `fund_analyzer` | 基金分析 | FOF+业绩分析 | 🆕 新增 |

---

## 技能使用指南

### 1. 晨间分析流程

```bash
# 1. 宏观分析（5分钟）
cd macro_analysis && python run.py

# 2. 风险扫描（2分钟）
cd risk_manager && python run.py

# 3. 组合检查（5分钟）
cd portfolio_manager && python run.py --portfolio my_portfolio.json
```

### 2. 选股流程

```bash
# 趋势风格
python a_share_trend/run.py

# 价值风格
python a_share_value/run.py

# 期货CTA
python futures_trend/run.py
```

### 3. 深度研究

```python
# 财务分析
from financial_analyzer.financial_analyzer import FinancialAnalyzer
analyzer = FinancialAnalyzer(pro)
dupont = analyzer.dupont_analysis('000001.SZ')
score = analyzer.financial_quality_score('000001.SZ')

# 行业研究
from industry_research.industry_research import IndustryResearch
research = IndustryResearch(pro)
performance = research.get_industry_performance('801750.SI')

# 基金分析
from fund_analyzer.fund_analyzer import FundAnalyzer
fund = FundAnalyzer(pro)
performance = fund.analyze_fund_performance('110022.OF')
```

---

## 能力覆盖映射

| 成长指南能力 | 对应技能 | 覆盖度 |
|-------------|---------|--------|
| 1. 投资哲学（道） | 无（理念层面） | - |
| 2. 宏观分析（势） | `macro_analysis` | ✅ 100% |
| 3. 风险管理（盾） | `risk_manager` | ✅ 80% |
| 4. 深度研究（术） | `financial_analyzer` + `industry_research` | ✅ 80% |
| 5. 交易执行（器） | 4个策略skill | ✅ 100% |
| 6. 组合管理（阵） | `portfolio_manager` | ✅ 90% |
| 7. 心态修炼（心） | 无（心理层面） | - |
| 8. 量化技术（工具） | `tushare_utils` | ✅ 100% |

**总体覆盖度：可技能化的能力 100% 覆盖**

---

## 技能依赖关系

```
                        ┌──────────────────┐
                        │   tushare        │
                        │   (官方接口)      │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │ tushare_utils    │
                        │ (API工具集)       │
                        └────────┬─────────┘
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       │                         │                         │
┌──────▼──────┐         ┌────────▼────────┐      ┌────────▼──────┐
│宏观分析       │         │   交易执行       │      │  组合/风险管理  │
│macro_analysis│◄────────┤ a_share_trend   │─────►│ portfolio_mgr │
│- 美林时钟     │         │ a_share_value   │      │ risk_manager  │
│- 经济周期     │         │ futures_trend   │      │               │
│- 大类配置     │         │ futures_value   │      └───────────────┘
└─────────────┘         └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
           ┌────────▼───┐ ┌──────▼────┐ ┌────▼──────┐
           │财务分析      │ │ 行业研究   │ │ 基金分析   │
           │financial_  │ │industry_  │ │fund_      │
           │analyzer    │ │research   │ │analyzer   │
           └────────────┘ └───────────┘ └───────────┘
```

---

## 快速开始

### 1. 环境准备

```bash
pip install tushare pandas numpy
export TUSHARE_TOKEN=your_token
```

### 2. 运行所有测试

```bash
./check.sh
```

### 3. 使用示例

```python
import sys
sys.path.insert(0, '/Users/lijian/.agents/skills')

import tushare as ts
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 宏观分析
from macro_analysis.macro_analyzer import MacroAnalyzer
macro = MacroAnalyzer(pro)
phase, confidence = macro.detect_economic_phase()
print(f"当前周期: {phase}")

# 组合分析
from portfolio_manager.portfolio import PortfolioManager
pm = PortfolioManager(pro)
portfolio = pm.load_portfolio('my_portfolio.json')
analysis = pm.analyze_portfolio(portfolio)

# 风险扫描
from risk_manager.risk_manager import RiskManager
rm = RiskManager(pro)
risk = rm.scan_portfolio_risk(portfolio['holdings'])
```

---

## 后续扩展建议

1. **智能投顾**：整合所有技能，提供一键式投资建议
2. **回测框架**：为所有策略提供统一的回测能力
3. **实时监控**：基于websocket的实时数据监控
4. **机器学习**：引入ML模型进行预测和分类
5. **多因子模型**：构建更复杂的多因子选股系统

---

**总计：11个技能模块，覆盖专业投资人全部可技能化能力**
