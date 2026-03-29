# financial_analyzer - 财务深度分析

基于上市公司财务报表的深度分析系统，提供杜邦分析、财务质量评分、同业比较等功能。

> **skill名称**: `financial_analyzer` (财务深度分析)
> **分析方法**: 杜邦分析、财务质量评分
> **数据来源**: Tushare财务报表数据
> **适用场景**: 个股深度研究、财务风险识别

---

## 概述

本技能是一个完整的财务分析系统，核心特点：

- **杜邦分析**: ROE拆解（净利润率 × 资产周转率 × 权益乘数）
- **财务质量评分**: 多维度评分（盈利/现金流/杠杆/成长）
- **同业比较**: 行业分位数对比

### 核心指标

| 指标 | 说明 | 健康标准 |
|------|------|---------|
| ROE | 净资产收益率 | >15%优秀 |
| 净利率 | 净利润/营收 | 行业差异大 |
| 资产周转率 | 营收/总资产 | >0.5较好 |
| 权益乘数 | 总资产/净资产 | 2-3合理 |
| 现金流/净利润 | 盈利质量 | >0.8健康 |

---

## 使用方法

### Python调用

```python
import sys
sys.path.insert(0, '/path/to/skills')

from financial_analyzer.financial_analyzer import FinancialAnalyzer
import tushare as ts

pro = ts.pro_api()
analyzer = FinancialAnalyzer(pro)

# 杜邦分析
dupont = analyzer.dupont_analysis('000001.SZ')
print(f"ROE: {dupont['roe']:.2f}%")
print(f"净利润率: {dupont['net_profit_margin']:.2f}%")
print(f"资产周转率: {dupont['asset_turnover']:.2f}")
print(f"权益乘数: {dupont['equity_multiplier']:.2f}")

# 财务质量评分
quality = analyzer.financial_quality_score('000001.SZ')
print(f"总评分: {quality['total_score']:.1f}")
print(f"等级: {quality['grade']}")
```

---

## 输出示例

```
【杜邦分析】 000001.SZ 平安银行
ROE: 12.50%
  ├─ 净利润率: 25.00%
  ├─ 资产周转率: 0.04
  └─ 权益乘数: 12.50

【财务质量评分】
总评分: 75.2 (B级)
├─ 盈利能力: 80.0
├─ 现金流质量: 70.0
├─ 杠杆水平: 75.0
└─ 成长能力: 65.0
```

---

## 数据来源

| 数据 | Tushare接口 | 更新频率 |
|------|------------|---------|
| 财务指标 | `fina_indicator` | 季度 |
| 公司信息 | `stock_basic` | 日度 |

---

## 更新日志

### 2026-03-29 v1.0
- 发布初始版本
- 实现杜邦分析和财务质量评分
