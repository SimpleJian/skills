# 更新日志

## 2026-03-29 - 数据质量与风险标签系统

### 新增功能

#### 1. 数据质量检查模块 (`tushare_utils/data_quality.py`)
- **价格数据质量检查**
  - 除权缺口检测（单日涨跌>20%）
  - 停牌标记（volume=0）
  - 价格连续性检查（跳空>7天）
  - 异常值检测（零值/负值）
  
- **财务数据异常检测**
  - 应收账款异常（增速>营收增速×1.5）
  - 现金流质量差（经营现金流/净利润<0.6）
  - 存贷双高检测（现金>20%资产且负债>30%）
  - 高商誉检测（商誉>30%资产）
  - 盈利波动大（ROE标准差>10）

- **数据预处理功能**
  - 新股/次新股过滤（上市<60日）
  - 波动率标签计算
  - 停牌状态标记

- **期货合约到期检查**
  - 自动解析合约到期月份
  - 剩余天数计算
  - 到期提醒（<7天极高风险，<15天临近换月）

#### 2. 风险标签系统 (`tushare_utils/risk_tags.py`)
- **5大类风险分类**
  - 财务风险：应收账款异常、现金流质量差、存贷双高等
  - 流动性风险：成交额过低、即将到期、临近换月等
  - 政策风险：ST风险、行业衰退期
  - 数据质量：除权缺口、新股、近期停牌
  - 波动风险：极高波动（年化>60%）、高波动（年化>40%）、异动

- **风险等级**
  - 极高风险（CRITICAL）：即将到期合约、极高波动
  - 高风险（HIGH）：财务异常、临近换月
  - 中风险（MEDIUM）：数据质量问题
  - 低风险（LOW）：新股标记

- **标签输出格式**
  - 多标签以 `|` 分隔
  - 按风险等级排序
  - 可限制返回标签数量

#### 3. 财务数据持久化缓存 (`tushare_utils/api_utils.py`)
- **缓存特性**
  - 本地文件存储：`~/.cache/tushare/financial/`
  - 默认90天有效期（约一个季度）
  - 自动增量更新
  - 去重处理（保留最新数据）

- **缓存管理**
  - 缓存统计信息
  - 过期缓存自动清理
  - 元数据管理

### 修改内容

#### 1. A股趋势跟踪策略 (`a_share_trend/stock_selector.py`)
- 集成数据质量检查
- 输出增加 `risk_tags` 列
- 自动标记波动风险和数据质量问题

#### 2. A股价值抄底策略 (`a_share_value/value_selector.py`)
- 集成数据质量检查
- 财务异常红旗检测
- 输出增加 `risk_tags` 列

#### 3. 期货趋势跟踪策略 (`futures_trend/`)
- `futures_selector.py`: 集成合约到期检查、风险标签
- `portfolio_builder.py`: 输出显示 `risk_tags` 列
- 自动跳过即将到期合约（<7天）

#### 4. 期货价值抄底策略 (`futures_value/`)
- `futures_value_selector.py`: 集成风险标签
- `value_scorer.py`: 支持风险标签传入

### 新增测试

#### 测试文件
- `tests/test_data_quality.py`: 38个测试用例
- `tests/test_risk_tags.py`: 风险标签系统测试
- `tests/test_financial_cache.py`: 财务缓存测试

#### 运行测试
```bash
cd /path/to/skills

# 运行所有测试
python tests/run_tests.py

# 详细输出
python tests/run_tests.py -v

# 只运行特定测试
python tests/run_tests.py -k test_data_quality
```

### 输出示例

**修改前：**
```
ts_code    name    industry  total_score
000001.SZ  平安银行  银行       85
```

**修改后：**
```
ts_code    name    industry  total_score  risk_tags
000001.SZ  平安银行  银行       85         高波动|近期停牌
```

### 技术改进

1. **动态路径获取**: 所有模块使用 `os.path.abspath(__file__)` 获取路径，不再硬编码
2. **错误处理增强**: API调用失败时指数退避重试
3. **类型安全**: 修复了 DataFrame 布尔判断的歧义问题
4. **缓存类型安全**: 确保日期字段为字符串类型，避免排序错误

### 后续建议

1. **定期运行测试**: 每次修改后运行 `python tests/run_tests.py`
2. **监控缓存大小**: 定期清理 `~/.cache/tushare/financial/`
3. **更新风险标签**: 根据实际使用情况调整风险阈值
4. **扩展测试覆盖**: 为各策略的核心逻辑添加更多测试
