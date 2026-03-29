# industry_research - 行业研究

基于产业链分析和行业景气度的研究系统，提供行业轮动、波特五力分析等功能。

> **skill名称**: `industry_research` (行业研究)
> **分析框架**: 产业链分析、波特五力
> **适用场景**: 行业配置、主题投资、产业链研究

---

## 概述

本技能是一个完整的行业研究系统，核心特点：

- **产业链分析**: 上中下游产业链映射
- **行业轮动**: 识别领先/落后行业
- **波特五力**: 行业竞争格局分析
- **景气度跟踪**: 行业表现监控

### 产业链映射

| 产业链 | 上游 | 中游 | 下游 |
|--------|------|------|------|
| 新能源汽车 | 锂矿/钴矿 | 电池/电机 | 整车 |
| 半导体 | 硅片/设备 | 设计/制造 | 封测/应用 |
| 光伏 | 硅料 | 硅片/电池片 | 组件/电站 |

---

## 使用方法

### Python调用

```python
import sys
sys.path.insert(0, '/path/to/skills')

from industry_research.industry_research import IndustryResearch
import tushare as ts

pro = ts.pro_api()
research = IndustryResearch(pro)

# 行业表现
perf = research.get_industry_performance('801750.SI')
print(f"行业收益: {perf['total_return']:.2f}%")

# 行业轮动
rotation = research.industry_rotation()
print(f"领先行业: {rotation['leading']}")
print(f"落后行业: {rotation['lagging']}")

# 波特五力分析
forces = research.porter_five_forces('新能源汽车')
```

---

## 输出示例

```
【行业轮动分析】
领先行业: 科技、新能源
落后行业: 地产、银行
轮动信号: 成长风格占优

【波特五力分析】 新能源汽车
行业内竞争: 激烈
新进入者威胁: 中等
替代品威胁: 低
买方议价能力: 中等
供应商议价能力: 高
```

---

## 数据来源

| 数据 | Tushare接口 | 更新频率 |
|------|------------|---------|
| 行业指数 | `sw_daily` | 日度 |
| 行业分类 | `stock_basic` | 日度 |

---

## 更新日志

### 2026-03-29 v1.0
- 发布初始版本
- 实现产业链和波特五力分析
