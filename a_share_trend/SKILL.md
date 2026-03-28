# a_share_trend - A股趋势跟踪主线选股策略

基于行情集中度指标识别市场主线，通过"三步筛选法"精选标的，配合多因子评分模型动态管理仓位的系统性投资框架。

> **skill名称**: `a_share_trend` (A股趋势选股)

---

## 概述

本策略是一个完整的A股趋势跟踪选股系统，核心特点：

- **行情集中度指标**：量化识别市场主线方向
- **三步筛选法**：安全关+动量关 → 资金关+题材关+技术关 → 多因子评分排序
- **多因子评分模型**：趋势(40%) + 资金(30%) + 主题(20%) + 风险(10%)
- **动态仓位配置**：核心仓位(30-40%) + 卫星仓位(15-20%) + 观察仓位(5-10%)

---

## 核心概念

### 行情集中度指标

```
行情集中度 = 涨幅前30%个股涨幅均值 − 全市场涨幅中位数
```

**指标解读：**

| 指标区间 | 市场含义 | 策略应对 |
|---------|---------|---------|
| <-2% | 市场极度分散，无明确主线 | 降低仓位，观望等待 |
| -2% ~ 1% | 主线酝酿期 | 轻仓布局潜在方向 |
| 1% ~ 3% | 主线初步确立 | 加仓确认方向，持有龙头 |
| 3% ~ 5% | 主升浪展开 | 核心仓位持有，警惕过热 |
| >5% | 情绪泡沫化 | 逐步减仓，锁定利润 |

### 三步筛选法

**第一步：初步筛选（安全关 + 动量关）**

- 排除ST/*ST、退市风险、财务异常股票
- 20日新高突破（收盘高2%以上）
- 成交量放大（较20日均量放大1.5倍以上）
- 年线上方运行（250日均线）
- 板块集中度提升

**第二步：精确筛选（资金关 + 题材关 + 技术关）**

- 主力资金确认：北向资金、大单资金流入
- 主线题材匹配：所属板块处于集中度前列
- 技术形态精筛：MACD零轴上方、多头排列、无顶背离

**第三步：综合排序（多因子评分）**

- 趋势强度分（40分）：均线排列、MACD、突破、趋势一致性
- 资金认可度分（30分）：成交量、机构持仓、北向资金
- 主线契合度分（20分）：板块排名、题材催化强度
- 风险调整分（10分）：波动率、流动性

---

## 安装依赖

```bash
# 安装 Tushare
pip install tushare -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置 Tushare Token
export TUSHARE_TOKEN=your_token_here
```

获取 Tushare Token：[https://tushare.pro/register](https://tushare.pro/register)

---

## 快速开始

### 1. 使用选股器执行完整选股流程

```python
import tushare as ts
from stock_selector import StockSelector

# 初始化
pro = ts.pro_api()
selector = StockSelector(pro)

# 执行选股
result = selector.select_stocks(top_n=30, min_amount=1.0)

# 查看结果
print(result['selected_stocks'])
```

### 2. 单独使用各模块

#### 行情集中度分析

```python
from market_concentration import MarketConcentration

mc = MarketConcentration(pro)

# 计算当日集中度
concentration = mc.calculate_concentration()
print(f"行情集中度: {concentration['concentration']}%")

# 获取行业集中度排名
industries = mc.calculate_industry_concentration()
print(industries.head(10))

# 获取集中度趋势
trend = mc.get_concentration_trend(days=20)
```

#### 技术指标分析

```python
from technical_indicators import TechnicalIndicators

ti = TechnicalIndicators(pro)

# 获取个股技术面评分
score = ti.get_technical_score('000001.SZ')
print(f"技术面评分: {score['score']}")
print(f"风险信号: {score['risks']}")
```

#### 多因子评分

```python
from multi_factor_scorer import MultiFactorScorer

scorer = MultiFactorScorer(pro)

# 计算个股综合评分
result = scorer.calculate_total_score('000001.SZ', industry_concentration)
print(f"综合评分: {result['total_score']}")
print(f"趋势评分: {result['trend_score']['score']}")
print(f"资金评分: {result['fund_score']['score']}")
```

---

## 模块说明

### market_concentration.py - 行情集中度模块

**核心类：** `MarketConcentration`

**主要方法：**

| 方法 | 说明 |
|------|------|
| `calculate_concentration(trade_date)` | 计算指定日期行情集中度 |
| `calculate_industry_concentration(trade_date)` | 计算各行业板块集中度 |
| `get_concentration_trend(days)` | 获取近期集中度趋势 |
| `interpret_concentration(value)` | 解读集中度数值含义 |

### technical_indicators.py - 技术指标模块

**核心类：** `TechnicalIndicators`

**主要方法：**

| 方法 | 说明 |
|------|------|
| `get_technical_score(ts_code)` | 获取个股技术面综合评分 |
| `calculate_ma(df)` | 计算移动平均线 |
| `calculate_macd(df)` | 计算MACD指标 |
| `check_divergence(df)` | 检测MACD顶背离/底背离 |
| `check_breakthrough(df)` | 检测突破信号 |
| `analyze_volume(df)` | 成交量分析 |
| `check_ma_arrangement(df)` | 检查均线排列形态 |

### fundamental_filter.py - 基本面筛选模块

**核心类：** `FundamentalFilter`, `FundAnalysis`

**主要方法：**

| 方法 | 说明 |
|------|------|
| `get_all_risk_stocks(trade_date)` | 获取所有风险股票 |
| `filter_risk_stocks(stock_list)` | 过滤风险股票 |
| `get_north_bound_flow(trade_date)` | 获取北向资金流向 |
| `get_money_flow(ts_code)` | 获取个股资金流向 |
| `get_institutional_holding(ts_code)` | 获取机构持仓信息 |

### multi_factor_scorer.py - 多因子评分模块

**核心类：** `MultiFactorScorer`

**主要方法：**

| 方法 | 说明 |
|------|------|
| `calculate_total_score(ts_code)` | 计算个股综合评分 |
| `rank_stocks(stock_list)` | 对股票列表评分排名 |
| `calculate_trend_score(ts_code)` | 计算趋势强度分 |
| `calculate_fund_score(ts_code)` | 计算资金认可度分 |
| `calculate_theme_score(ts_code)` | 计算主线契合度分 |
| `calculate_risk_score(ts_code)` | 计算风险调整分 |

### stock_selector.py - 选股主模块

**核心类：** `StockSelector`

**主要方法：**

| 方法 | 说明 |
|------|------|
| `select_stocks(top_n, min_amount)` | 执行完整选股流程 |
| `step1_preliminary_filter(min_amount)` | 第一步：初步筛选 |
| `step2_precise_filter(stock_list)` | 第二步：精确筛选 |
| `step3_ranking(stock_list)` | 第三步：综合排序 |

---

## 选股输出示例

```
================================================================================
A股趋势跟踪主线选股策略
================================================================================

【行情集中度分析】
当前行情集中度: 3.25%
解读: 主升浪展开，资金极致集中 - 建议核心仓位持有，警惕过热

【行业集中度排名】
行业名称     集中度   涨停家数   上涨比例
电力设备      5.12%      12       78%
半导体        4.85%       8       72%
通信设备      4.63%       6       68%
...

第一步：初步筛选（安全关 + 动量关）
全市场股票数量: 5000
风险股票数量: 250
初步筛选后股票数量: 180

第二步：精确筛选（资金关 + 题材关 + 技术关）
精确筛选后股票数量: 45

第三步：综合排序（多因子评分）
评分完成，共 45 只股票

================================================================================
仓位配置建议
================================================================================

【核心仓位】建议配置 30%-40% 资金，5 只
 ts_code   name     industry     total_score
300750.SZ  宁德时代  电力设备        92.5
002594.SZ  比亚迪    汽车           89.3
600519.SH  贵州茅台  食品饮料        87.2
...

【卫星仓位】建议配置 15%-20% 资金，8 只
...

================================================================================
选股完成！耗时: 120.5 秒
================================================================================
```

---

## 止损止盈规则

### 硬性止损

- **技术止损**：跌破最近10日最低价
- **幅度止损**：自买入价下跌-8%（科创板/创业板-12%）

### 趋势止损

- **一级预警**：周线MACD死叉，减仓20%
- **二级确认**：均线空头排列形成，清仓

### 动态止盈

- **初始阶段**（盈利<20%）：不设止盈
- **动态保护**（盈利≥20%）：从最高点回撤10%止盈
- **加速收紧**（盈利≥50%）：回撤阈值收紧至5%-7%

---

## 注意事项

1. **数据更新**：Tushare数据通常有15分钟到1天的延迟，不适合高频交易

2. **权限要求**：部分接口需要Tushare积分或付费权限：
   - 分钟级数据
   - Level-2资金流向
   - 机构持仓明细

3. **市场状态**：策略在震荡市可能失效，建议结合行情集中度指标判断

4. **风险控制**：本策略仅供研究参考，不构成投资建议，请根据自身风险承受能力调整参数

---

## 策略优化建议

### 参数调优

根据市场波动率调整参数：

| 波动率环境 | 均线周期 | 止损幅度 |
|-----------|---------|---------|
| 高波动(>25%) | 短期3日，中期10日 | -10% |
| 正常(15%-25%) | 短期5日，中期20日 | -8% |
| 低波动(<15%) | 短期10日，中期60日 | -5% |

### 扩展功能

1. **加入板块轮动**：基于行业集中度变化动态调整板块权重
2. **消息面过滤**：结合新闻情绪分析过滤负面消息股票
3. **回测验证**：使用历史数据验证策略有效性
4. **实时监控**：设置定时任务，每日盘后自动运行选股

---

## API 参考

### Tushare 主要接口

| 接口 | 用途 |
|------|------|
| `pro.daily()` | 获取日线行情 |
| `pro.stock_basic()` | 获取股票基础信息 |
| `pro.fina_indicator()` | 获取财务指标 |
| `pro.moneyflow()` | 获取资金流向 |
| `pro.hk_hold()` | 获取沪深港通持股 |
| `pro.index_classify()` | 获取行业分类 |
| `pro.index_member()` | 获取指数成分股 |

---

## 相关资源

- [Tushare官方文档](https://tushare.pro/document/2)
- [策略原理详解](https://tushare.pro/document/2?doc_id=255)

---

## License

MIT License - 仅供学习和研究使用
