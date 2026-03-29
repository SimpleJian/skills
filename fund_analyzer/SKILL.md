# fund_analyzer - 基金分析

基于基金业绩和持仓的FOF分析系统，提供基金筛选、业绩分析、持仓穿透等功能。

> **skill名称**: `fund_analyzer` (基金分析)
> **分析维度**: 业绩/风险/持仓/风格
> **适用场景**: FOF配置、基金定投、业绩归因

---

## 概述

本技能是一个完整的基金分析系统，核心特点：

- **基金筛选**: 按类型/业绩/规模筛选
- **业绩分析**: 收益/风险/夏普比率
- **持仓穿透**: 基金底层资产配置
- **风格分析**: 价值/成长/大盘/小盘

### 核心指标

| 指标 | 说明 | 优秀标准 |
|------|------|---------|
| 年化收益 | 年度收益率 | >15% |
| 夏普比率 | 风险调整后收益 | >1.0 |
| 最大回撤 | 峰值到谷底 | <20% |
| 信息比率 | 相对基准超额 | >0.5 |

---

## 使用方法

### Python调用

```python
import sys
sys.path.insert(0, '/path/to/skills')

from fund_analyzer.fund_analyzer import FundAnalyzer
import tushare as ts

pro = ts.pro_api()
fa = FundAnalyzer(pro)

# 基金筛选
funds = fa.filter_funds(fund_type='E')  # 股票型

# 业绩分析
perf = fa.analyze_fund_performance('110022.OF')
print(f"总收益: {perf['total_return']:.2f}%")
print(f"夏普比率: {perf['sharpe']:.2f}")

# 持仓穿透
portfolio = fa.get_fund_portfolio('110022.OF')
```

---

## 输出示例

```
【基金业绩分析】 110022.OF
总收益率: 45.20%
年化收益: 18.50%
年化波动: 22.30%
夏普比率: 0.83
最大回撤: -18.50%

【前十大持仓】
1. 贵州茅台 8.5%
2. 五粮液 7.2%
3. 泸州老窖 6.8%
...
```

---

## 数据来源

| 数据 | Tushare接口 | 更新频率 |
|------|------------|---------|
| 基金基础信息 | `fund_basic` | 日度 |
| 基金净值 | `fund_nav` | 日度 |
| 基金持仓 | `fund_portfolio` | 季度 |

---

## 更新日志

### 2026-03-29 v1.0
- 发布初始版本
- 实现基金筛选和业绩分析
