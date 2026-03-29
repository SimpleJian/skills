# tushare_utils - Tushare API 工具集

Tushare API 频率控制与数据获取工具集，解决 API 调用频率限制问题，提供缓存、重试、批量获取等功能。

> **skill名称**: `tushare_utils`
> **用途**: API 频率控制、数据缓存、批量获取
> **依赖**: tushare, pandas, numpy

---

## 概述

使用 Tushare API 时，免费用户通常面临每分钟 500 次的频率限制。本工具集提供以下功能：

- **频率限制控制**: 自动控制 API 调用间隔，避免触发限制
- **自动重试机制**: 遇到频率限制时自动等待并重试
- **数据缓存**: 缓存基础数据，减少重复请求
- **批量获取**: 分批获取数据，自动添加延时
- **API 包装器**: 一站式解决频率控制+缓存问题

---

## 安装与配置

### 依赖安装

```bash
pip install tushare pandas numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 环境变量

```bash
export TUSHARE_TOKEN=your_token_here
```

---

## 使用方法

### 1. 基础频率限制

```python
import sys
sys.path.insert(0, '/path/to/skills')
from tushare_utils.api_utils import APIRateLimiter

import tushare as ts

# 初始化 Tushare
ts.set_token('your_token')
pro = ts.pro_api()

# 创建频率限制器（60秒内最多400次）
limiter = APIRateLimiter(max_calls=400, period=60)

# 使用装饰器
@limiter.rate_limit
def get_stock_data(ts_code):
    return pro.daily(ts_code=ts_code)

# 调用函数（自动频率控制）
df = get_stock_data('000001.SZ')
```

### 2. 自动重试装饰器

```python
from tushare_utils.api_utils import retry_on_rate_limit

# 遇到频率限制时自动重试（最多3次，每次等待10秒）
@retry_on_rate_limit(max_retries=3, sleep_time=10)
def get_data_with_retry(ts_code):
    return pro.daily(ts_code=ts_code)

df = get_data_with_retry('000001.SZ')
```

### 3. API 包装器（推荐）

```python
from tushare_utils.api_utils import TushareAPIWrapper

# 创建包装器（自动频率控制+缓存）
wrapper = TushareAPIWrapper(pro, max_calls=400, period=60)

# 使用包装器调用 API（自动频率控制）
df = wrapper.daily(ts_code='000001.SZ')
df = wrapper.stock_basic()
df = wrapper.daily_basic(trade_date='20250101')

# 基础数据会自动缓存
df1 = wrapper.stock_basic()  # 第一次从 API 获取
df2 = wrapper.stock_basic()  # 第二次从缓存获取（更快）

# 清理缓存
wrapper.clear_cache()
```

### 4. 批量获取数据

```python
from tushare_utils.api_utils import batch_fetch_data

# 定义获取函数
def fetch_stock_data(ts_code):
    return pro.daily(ts_code=ts_code)

# 批量获取（自动分批+延时）
stock_list = ['000001.SZ', '000002.SZ', '000003.SZ', ...]  # 100只股票

results = batch_fetch_data(
    fetch_func=fetch_stock_data,
    items=stock_list,
    batch_size=50,      # 每批50只
    sleep_time=0.2      # 批次间等待0.2秒
)
```

### 5. 数据缓存

```python
from tushare_utils.api_utils import APICache

# 创建缓存（有效期300秒）
cache = APICache(ttl=300)

# 检查缓存
cached = cache.get('daily', '000001.SZ')
if cached is not None:
    print("使用缓存数据")
    df = cached
else:
    print("从 API 获取")
    df = pro.daily(ts_code='000001.SZ')
    cache.set('daily', df, '000001.SZ')

# 清理过期缓存
cache.clear()
```

### 6. 全局单例包装器

```python
from tushare_utils.api_utils import get_api_wrapper

# 获取全局包装器实例（单例模式）
wrapper = get_api_wrapper(pro, max_calls=400, period=60)

# 整个程序使用同一个频率限制器
df1 = wrapper.daily(ts_code='000001.SZ')
df2 = wrapper.daily(ts_code='000002.SZ')
```

---

## API 参考

### APIRateLimiter

频率限制器类。

```python
APIRateLimiter(max_calls=400, period=60)
```

**参数**:
- `max_calls`: 时间周期内最大调用次数（默认400）
- `period`: 时间周期（秒，默认60）

**方法**:
- `rate_limit(func)`: 装饰器，应用于需要频率控制的函数

### retry_on_rate_limit

自动重试装饰器。

```python
@retry_on_rate_limit(max_retries=3, sleep_time=10)
def my_function():
    pass
```

**参数**:
- `max_retries`: 最大重试次数（默认3）
- `sleep_time`: 等待时间（秒，默认10）

### TushareAPIWrapper

API 包装器类，集成频率控制+缓存。

```python
TushareAPIWrapper(pro_api, max_calls=400, period=60)
```

**方法**:
- `daily(**kwargs)`: 获取日线数据
- `stock_basic(**kwargs)`: 获取股票基础信息
- `daily_basic(**kwargs)`: 获取每日指标
- `fut_basic(**kwargs)`: 获取期货基础信息
- `fut_daily(**kwargs)`: 获取期货日线数据
- `fina_indicator(**kwargs)`: 获取财务指标
- `clear_cache()`: 清理缓存

### batch_fetch_data

批量获取数据函数。

```python
batch_fetch_data(fetch_func, items, batch_size=50, sleep_time=0.2)
```

**参数**:
- `fetch_func`: 数据获取函数
- `items`: 待获取的项目列表
- `batch_size`: 每批处理数量（默认50）
- `sleep_time`: 批次间延时（秒，默认0.2）

**返回**:
- 结果列表

### APICache

数据缓存类。

```python
APICache(ttl=300)
```

**参数**:
- `ttl`: 缓存有效期（秒，默认300）

**方法**:
- `get(func_name, *args, **kwargs)`: 获取缓存
- `set(func_name, data, *args, **kwargs)`: 设置缓存
- `clear()`: 清理所有缓存

---

## 使用示例

### 示例 1：股票列表评分（带频率控制）

```python
import sys
sys.path.insert(0, '/path/to/skills')
from tushare_utils.api_utils import APIRateLimiter, batch_fetch_data
import tushare as ts

ts.set_token('your_token')
pro = ts.pro_api()

# 获取股票列表
stock_basic = pro.stock_basic(list_status='L')
stock_list = stock_basic['ts_code'].tolist()[:100]  # 前100只

# 定义评分函数
limiter = APIRateLimiter(max_calls=300, period=60)

@limiter.rate_limit
def score_stock(ts_code):
    df = pro.daily(ts_code=ts_code)
    if len(df) > 0:
        return {
            'ts_code': ts_code,
            'score': df['close'].mean()  # 示例评分
        }
    return None

# 批量评分
results = batch_fetch_data(
    fetch_func=score_stock,
    items=stock_list,
    batch_size=30,
    sleep_time=0.5
)

print(f"评分完成: {len(results)} 只股票")
```

### 示例 2：多因子数据获取（带缓存）

```python
from tushare_utils.api_utils import TushareAPIWrapper

wrapper = TushareAPIWrapper(pro, max_calls=400, period=60)

# 获取多维度数据（自动缓存）
# 技术面数据
df_daily = wrapper.daily(ts_code='000001.SZ')

# 基本面数据（自动缓存，重复获取更快）
df_basic = wrapper.daily_basic(trade_date='20250101')

# 财务数据
df_fina = wrapper.fina_indicator(ts_code='000001.SZ')
```

### 示例 3：高频数据获取（严格频率控制）

```python
from tushare_utils.api_utils import APIRateLimiter

# 更严格的频率控制（每分钟200次）
strict_limiter = APIRateLimiter(max_calls=200, period=60)

@strict_limiter.rate_limit
def get_minute_data(ts_code):
    return pro.stk_mins(ts_code=ts_code, freq='1min')

# 获取分钟数据
df = get_minute_data('000001.SZ')
```

---

## 配置建议

### 免费用户配置

```python
# 保守配置，确保不触发限制
limiter = APIRateLimiter(max_calls=300, period=60)  # 每分钟300次
wrapper = TushareAPIWrapper(pro, max_calls=300, period=60)
```

### 积分用户配置

```python
# 根据积分等级调整
# 1000积分以上
limiter = APIRateLimiter(max_calls=800, period=60)

# 5000积分以上
limiter = APIRateLimiter(max_calls=1500, period=60)
```

### 多技能共享配置

```python
from tushare_utils.api_utils import get_api_wrapper

# 使用单例模式，确保多个 skill 共享同一个频率限制器
wrapper = get_api_wrapper(pro, max_calls=400, period=60)

# 在 skill A 中使用
from tushare_utils.api_utils import get_api_wrapper
wrapper_a = get_api_wrapper(pro)  # 返回已创建的实例

# 在 skill B 中使用
from tushare_utils.api_utils import get_api_wrapper
wrapper_b = get_api_wrapper(pro)  # 返回同一个实例
```

---

## 故障排除

### 问题 1：仍然遇到频率限制

**解决**: 降低 `max_calls` 参数，增加延时

```python
limiter = APIRateLimiter(max_calls=200, period=60)  # 更保守的设置
```

### 问题 2：运行速度太慢

**解决**: 
1. 使用缓存避免重复请求
2. 增加 `max_calls`（如果积分足够）
3. 批量获取代替逐个获取

### 问题 3：缓存数据过期

**解决**: 调整 `ttl` 参数或手动清理缓存

```python
# 缩短缓存时间
cache = APICache(ttl=60)  # 1分钟

# 或手动清理
wrapper.clear_cache()
```

---

## 相关资源

- Tushare 官方文档: https://tushare.pro/document/2
- 积分获取说明: https://tushare.pro/document/1?doc_id=108
- API 权限查询: https://tushare.pro/document/2?doc_id=139

---

## 更新日志

### v1.0.0 (2026-03-28)

- 初始版本发布
- 提供频率限制、自动重试、数据缓存、批量获取功能
- 支持 A股、期货数据获取

---

## License

MIT License - 自由使用和修改
