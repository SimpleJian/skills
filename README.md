# Skills 总览

A股与期货量化投资策略集合，包含趋势跟踪、价值抄底等多种策略，以及 Tushare API 工具集。

---

## 📊 Skill 列表

### 1. A股策略

| Skill | 名称 | 风格 | 核心逻辑 | 适用场景 |
|-------|------|------|----------|----------|
| `a_share_trend` | A股趋势跟踪 | 追涨杀跌 | 行情集中度+均线突破+MACD | 牛市、强势市场 |
| `a_share_value` | A股价值抄底 | 逆向投资 | PE/PB/股息率+ROE+现金流 | 震荡市、熊市后期 |

### 2. 期货策略

| Skill | 名称 | 风格 | 核心逻辑 | 适用场景 |
|-------|------|------|----------|----------|
| `futures_trend` | 期货趋势跟踪 | 追涨杀跌 | 三层筛选+多因子评分+多空配置 | 趋势明确的市场 |
| `futures_value` | 期货价值抄底 | 逆向投资 | 技术面超卖+基本面价值+情绪验证 | 流动性冲击后的错杀 |

### 3. 工具类

| Skill | 名称 | 功能 | 说明 |
|-------|------|------|------|
| `tushare` | Tushare 数据接口 | 数据获取 | Tushare官方接口封装 |
| `tushare_utils` | Tushare 工具集 | 频率控制 | ⭐ API频率限制、缓存、批量获取 |

---

## 🚀 快速开始

### 环境准备

```bash
# 安装依赖
pip install tushare pandas numpy -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置 Token
export TUSHARE_TOKEN=your_token_here
```

### 运行策略

```bash
cd /path/to/skills  # 替换为你的 skills 目录路径

# A股趋势跟踪
python3 a_share_trend/run.py

# A股价值抄底
python3 a_share_value/run.py

# 期货趋势跟踪
python3 futures_trend/run.py

# 期货价值抄底
python3 futures_value/run.py
```

---

## 📈 策略对比

### 趋势策略 vs 价值策略

| 维度 | 趋势策略 | 价值策略 |
|------|---------|---------|
| **投资哲学** | 顺势而为 | 逆向投资 |
| **入场时机** | 趋势确立后 | 价格超跌时 |
| **核心指标** | 动量、均线、ADX | RSI、估值、成本支撑 |
| **持仓周期** | 数周至数月 | 2-6个月 |
| **胜率** | 35-45% | 50-60%（但可能提前） |
| **盈亏比** | 高（让利润奔跑） | 中高（价值回归） |

### A股 vs 期货

| 维度 | A股 | 期货 |
|------|-----|------|
| **多空** | 单向（做多） | 双向（多空） |
| **杠杆** | 无 | 有（10-20倍） |
| **T+1** | 是 | 否（T+0） |
| **期限** | 长期持有 | 合约到期需移仓 |

---

## ⚠️ 重要提示

### API 频率限制

所有策略已集成 `tushare_utils` 频率控制：
- 自动延时控制（默认 0.15 秒/次）
- 自动重试（遇到限制等待 10 秒）
- 数据缓存（基础数据缓存 5-10 分钟）
- 批量处理（分批获取，自动延时）

**预计运行时间**：
- A股策略：3-10 分钟
- 期货策略：3-8 分钟

### 风险提示

1. **本策略仅供研究学习，不构成投资建议**
2. 期货交易风险极高，杠杆可能放大亏损
3. 历史表现不代表未来收益
4. 投资有风险，入市需谨慎

---

## 📁 目录结构

```
/Users/lijian/.agents/skills/
├── a_share_trend/          # A股趋势跟踪策略
│   ├── SKILL.md
│   ├── run.py
│   ├── market_concentration.py
│   ├── technical_indicators.py
│   ├── fundamental_filter.py
│   ├── multi_factor_scorer.py
│   └── stock_selector.py
│
├── a_share_value/          # A股价值抄底策略
│   ├── SKILL.md
│   ├── run.py
│   ├── valuation_filter.py
│   ├── quality_filter.py
│   ├── growth_analyzer.py
│   ├── value_scorer.py
│   └── value_selector.py
│
├── futures_trend/          # 期货趋势跟踪策略
│   ├── SKILL.md
│   ├── run.py
│   ├── liquidity_filter.py
│   ├── trend_direction.py
│   ├── trend_strength.py
│   ├── portfolio_builder.py
│   └── futures_selector.py
│
├── futures_value/          # 期货价值抄底策略
│   ├── SKILL.md
│   ├── run.py
│   ├── technical_oversold.py
│   ├── fundamental_value.py
│   ├── sentiment_verification.py
│   ├── value_scorer.py
│   └── futures_value_selector.py
│
├── tushare_utils/          # Tushare 工具集
│   ├── SKILL.md
│   └── api_utils.py
│
├── tushare/                # Tushare 官方 skill
│   └── SKILL.md
│
├── README.md               # 本文件
└── API_RATE_LIMIT_GUIDE.md # API 频率限制解决方案
```

---

## 🔧 开发工具

### 使用 tushare_utils

```python
import sys
sys.path.insert(0, '/path/to/skills')  # 替换为你的 skills 目录路径
from tushare_utils.api_utils import APIRateLimiter, TushareAPIWrapper

# 频率控制
limiter = APIRateLimiter(max_calls=400, period=60)

@limiter.rate_limit
def get_data():
    return pro.daily(ts_code='000001.SZ')

# API 包装器（推荐）
wrapper = TushareAPIWrapper(pro, max_calls=400, period=60)
df = wrapper.daily(ts_code='000001.SZ')  # 自动频率控制+缓存
```

---

## 📚 相关资源

- [Tushare 官网](https://tushare.pro/)
- [Tushare 文档](https://tushare.pro/document/2)
- [量化投资书籍](https://book.douban.com/subject/25811312/)

---

## 📝 更新日志

### 2026-03-28

- 发布 v1.0 版本
- 包含 4 个策略 skill + 2 个工具 skill
- 集成 API 频率控制解决方案

---

## License

MIT License - 仅供学习和研究使用
