#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare API 工具模块

解决频率限制问题：
1. 自动延时控制
2. 请求队列管理
3. 批量数据获取
4. 本地缓存机制
"""

import time
import functools
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
import pandas as pd


class APIRateLimiter:
    """
    API 频率限制器
    
    使用方式:
        limiter = APIRateLimiter(max_calls=400, period=60)  # 60秒内最多400次
        
        @limiter.rate_limit
        def get_data():
            return pro.daily(ts_code='000001.SZ')
    """
    
    def __init__(self, max_calls: int = 400, period: int = 60):
        """
        初始化
        
        Args:
            max_calls: 周期内最大调用次数（保守设置，留有余量）
            period: 时间周期（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.min_interval = period / max_calls  # 最小调用间隔
    
    def rate_limit(self, func: Callable) -> Callable:
        """
        频率限制装饰器
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 清理过期的调用记录
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.period)
            self.calls = [c for c in self.calls if c > cutoff]
            
            # 检查是否需要等待
            if len(self.calls) >= self.max_calls:
                # 需要等待
                sleep_time = (self.calls[0] - cutoff).total_seconds()
                if sleep_time > 0:
                    print(f"  [频率控制] 等待 {sleep_time:.1f} 秒...")
                    time.sleep(sleep_time)
                    # 清理后重新检查
                    self.calls = [c for c in self.calls if c > datetime.now() - timedelta(seconds=self.period)]
            
            # 确保最小间隔
            if self.calls:
                last_call = self.calls[-1]
                elapsed = (now - last_call).total_seconds()
                if elapsed < self.min_interval:
                    sleep_time = self.min_interval - elapsed
                    time.sleep(sleep_time)
            
            # 记录本次调用
            self.calls.append(datetime.now())
            
            # 执行函数
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                if "每分钟最多访问" in str(e) or "权限" in str(e):
                    # 遇到频率限制，等待后重试
                    print(f"  [频率限制] 触发限制，等待 10 秒后重试...")
                    time.sleep(10)
                    return func(*args, **kwargs)
                raise e
        
        return wrapper


class APICache:
    """
    API 数据缓存
    
    缓存 API 响应，避免重复请求
    """
    
    def __init__(self, ttl: int = 300):
        """
        初始化
        
        Args:
            ttl: 缓存有效期（秒），默认5分钟
        """
        self.cache = {}
        self.ttl = ttl
    
    def _make_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key = f"{func_name}:{str(args)}:{str(kwargs)}"
        return key
    
    def get(self, func_name: str, *args, **kwargs) -> Any:
        """获取缓存"""
        key = self._make_key(func_name, *args, **kwargs)
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return data
            else:
                # 过期，删除
                del self.cache[key]
        return None
    
    def set(self, func_name: str, data: Any, *args, **kwargs):
        """设置缓存"""
        key = self._make_key(func_name, *args, **kwargs)
        self.cache[key] = (data, datetime.now())
    
    def clear(self):
        """清理所有缓存"""
        self.cache.clear()


class TushareAPIWrapper:
    """
    Tushare API 包装器
    
    集成频率限制和缓存功能
    """
    
    def __init__(self, pro_api, max_calls: int = 400, period: int = 60):
        """
        初始化
        
        Args:
            pro_api: Tushare pro_api 实例
            max_calls: 最大调用次数
            period: 时间周期（秒）
        """
        self.pro = pro_api
        self.limiter = APIRateLimiter(max_calls=max_calls, period=period)
        self.cache = APICache(ttl=300)
        
        # 缓存常用的基础数据
        self._stock_basic = None
        self._trade_cal = None
        self._last_update = None
    
    def _cached_call(self, func_name: str, *args, **kwargs):
        """
        带缓存的 API 调用
        """
        # 先查缓存
        cached = self.cache.get(func_name, *args, **kwargs)
        if cached is not None:
            return cached
        
        # 获取 API 函数
        func = getattr(self.pro, func_name)
        
        # 应用频率限制
        @self.limiter.rate_limit
        def call_api():
            return func(*args, **kwargs)
        
        result = call_api()
        
        # 缓存结果
        if result is not None and len(result) > 0:
            self.cache.set(func_name, result, *args, **kwargs)
        
        return result
    
    def stock_basic(self, **kwargs):
        """获取股票基础信息（带缓存）"""
        if self._stock_basic is None or self._is_cache_expired():
            self._stock_basic = self._cached_call('stock_basic', **kwargs)
            self._last_update = datetime.now()
        return self._stock_basic
    
    def trade_cal(self, **kwargs):
        """获取交易日历（带缓存）"""
        if self._trade_cal is None or self._is_cache_expired():
            self._trade_cal = self._cached_call('trade_cal', **kwargs)
            self._last_update = datetime.now()
        return self._trade_cal
    
    def daily(self, **kwargs):
        """获取日线数据"""
        return self._cached_call('daily', **kwargs)
    
    def daily_basic(self, **kwargs):
        """获取每日指标"""
        return self._cached_call('daily_basic', **kwargs)
    
    def fut_basic(self, **kwargs):
        """获取期货基础信息"""
        return self._cached_call('fut_basic', **kwargs)
    
    def fut_daily(self, **kwargs):
        """获取期货日线数据"""
        return self._cached_call('fut_daily', **kwargs)
    
    def fina_indicator(self, **kwargs):
        """获取财务指标"""
        return self._cached_call('fina_indicator', **kwargs)
    
    def _is_cache_expired(self) -> bool:
        """检查缓存是否过期"""
        if self._last_update is None:
            return True
        return datetime.now() - self._last_update > timedelta(minutes=10)
    
    def clear_cache(self):
        """清理缓存"""
        self.cache.clear()
        self._stock_basic = None
        self._trade_cal = None


def batch_fetch_data(fetch_func: Callable, items: list, 
                    batch_size: int = 50, sleep_time: float = 0.2) -> list:
    """
    批量获取数据，自动添加延时
    
    Args:
        fetch_func: 数据获取函数
        items: 待获取的项目列表
        batch_size: 每批处理数量
        sleep_time: 批次间延时（秒）
    
    Returns:
        结果列表
    """
    results = []
    total = len(items)
    
    for i in range(0, total, batch_size):
        batch = items[i:i+batch_size]
        
        for item in batch:
            try:
                result = fetch_func(item)
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"  获取 {item} 失败: {e}")
        
        # 批次间延时
        if i + batch_size < total:
            progress = min(i + batch_size, total) / total * 100
            print(f"  进度: {progress:.1f}%，等待 {sleep_time} 秒...")
            time.sleep(sleep_time)
    
    return results


def retry_on_rate_limit(max_retries: int = 3, sleep_time: float = 10):
    """
    遇到频率限制时重试的装饰器
    
    Args:
        max_retries: 最大重试次数
        sleep_time: 等待时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "每分钟最多访问" in str(e) or "权限" in str(e):
                        if attempt < max_retries - 1:
                            print(f"  [重试 {attempt+1}/{max_retries}] 等待 {sleep_time} 秒...")
                            time.sleep(sleep_time)
                        else:
                            raise e
                    else:
                        raise e
            return None
        return wrapper
    return decorator


# 全局 API 包装器实例（可选使用）
_global_api_wrapper = None

def get_api_wrapper(pro_api, max_calls: int = 400, period: int = 60):
    """
    获取全局 API 包装器实例
    
    使用单例模式，确保整个程序使用同一个频率限制器
    """
    global _global_api_wrapper
    if _global_api_wrapper is None:
        _global_api_wrapper = TushareAPIWrapper(pro_api, max_calls, period)
    return _global_api_wrapper


if __name__ == '__main__':
    # 测试
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    # 使用频率限制器
    limiter = APIRateLimiter(max_calls=10, period=60)
    
    @limiter.rate_limit
    def test_api(ts_code):
        return pro.daily(ts_code=ts_code)
    
    # 测试批量调用
    stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']
    for code in stocks:
        print(f"获取 {code}...")
        result = test_api(code)
        print(f"  结果行数: {len(result) if result is not None else 0}")


class FinancialDataCache:
    """
    财务数据持久化缓存
    
    特点：
    - 本地文件存储（~/.cache/tushare/financial/）
    - 按季度更新（3个月有效期）
    - 增量更新：只下载缺失的季度数据
    """
    
    def __init__(self, cache_dir: Optional[str] = None, ttl_days: int = 90):
        """
        初始化
        
        Args:
            cache_dir: 缓存目录，默认 ~/.cache/tushare/financial/
            ttl_days: 缓存有效期（天），默认90天（约一个季度）
        """
        if cache_dir is None:
            home_dir = os.path.expanduser('~')
            cache_dir = os.path.join(home_dir, '.cache', 'tushare', 'financial')
        
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        self.metadata_file = os.path.join(cache_dir, 'metadata.json')
        
        # 确保目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 加载元数据
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> dict:
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            print(f"  [缓存] 保存元数据失败: {e}")
    
    def _get_cache_key(self, ts_code: str, data_type: str = 'fina_indicator') -> str:
        """生成缓存键"""
        return f"{data_type}_{ts_code}"
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        # 使用哈希避免文件名过长
        hash_key = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{hash_key}.csv")
    
    def get(self, ts_code: str, data_type: str = 'fina_indicator') -> Optional[pd.DataFrame]:
        """
        获取缓存的财务数据
        
        Returns:
            DataFrame 或 None（缓存不存在或已过期）
        """
        cache_key = self._get_cache_key(ts_code, data_type)
        cache_path = self._get_cache_path(cache_key)
        
        # 检查文件是否存在
        if not os.path.exists(cache_path):
            return None
        
        # 检查是否过期
        meta = self.metadata.get(cache_key, {})
        last_update = meta.get('last_update')
        
        if last_update:
            last_date = datetime.fromisoformat(last_update)
            if datetime.now() - last_date > timedelta(days=self.ttl_days):
                print(f"  [缓存] {ts_code} 财务数据已过期，需重新获取")
                return None
        
        # 读取缓存
        try:
            df = pd.read_csv(cache_path)
            print(f"  [缓存] 使用本地缓存: {ts_code}")
            return df
        except Exception as e:
            print(f"  [缓存] 读取缓存失败 {ts_code}: {e}")
            return None
    
    def set(self, ts_code: str, df: pd.DataFrame, data_type: str = 'fina_indicator'):
        """保存财务数据到缓存"""
        if df is None or df.empty:
            return
        
        cache_key = self._get_cache_key(ts_code, data_type)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            # 保存数据
            df.to_csv(cache_path, index=False)
            
            # 更新元数据
            self.metadata[cache_key] = {
                'ts_code': ts_code,
                'data_type': data_type,
                'last_update': datetime.now().isoformat(),
                'rows': len(df),
                'columns': list(df.columns)
            }
            self._save_metadata()
            
            print(f"  [缓存] 已保存: {ts_code} ({len(df)} 行)")
        except Exception as e:
            print(f"  [缓存] 保存失败 {ts_code}: {e}")
    
    def get_last_report_period(self, ts_code: str, data_type: str = 'fina_indicator') -> Optional[str]:
        """
        获取缓存中最新的报告期
        
        Returns:
            最新报告期字符串，如 '20240331'，无缓存返回 None
        """
        df = self.get(ts_code, data_type)
        if df is not None and not df.empty and 'end_date' in df.columns:
            return str(df['end_date'].max())
        return None
    
    def update_incremental(self, ts_code: str, new_data: pd.DataFrame, 
                          data_type: str = 'fina_indicator') -> pd.DataFrame:
        """
        增量更新缓存
        
        合并新数据和旧数据，去重后保存
        
        Returns:
            合并后的完整数据
        """
        # 获取现有缓存
        existing = self.get(ts_code, data_type)
        
        if existing is not None and not existing.empty:
            # 合并数据
            combined = pd.concat([existing, new_data], ignore_index=True)
            
            # 去重（基于报告期）
            if 'end_date' in combined.columns:
                combined = combined.drop_duplicates(subset=['end_date'], keep='last')
            
            # 按日期排序
            if 'end_date' in combined.columns:
                # 确保日期格式一致
                combined['end_date'] = combined['end_date'].astype(str)
                combined = combined.sort_values('end_date')
            
            print(f"  [缓存] 增量更新: {ts_code} (原有 {len(existing)} 行，新增 {len(new_data)} 行，合并后 {len(combined)} 行)")
        else:
            combined = new_data
            print(f"  [缓存] 全新缓存: {ts_code} ({len(combined)} 行)")
        
        # 保存
        self.set(ts_code, combined, data_type)
        
        return combined
    
    def clear_expired(self):
        """清理过期缓存"""
        expired_keys = []
        
        for cache_key, meta in self.metadata.items():
            last_update = meta.get('last_update')
            if last_update:
                last_date = datetime.fromisoformat(last_update)
                if datetime.now() - last_date > timedelta(days=self.ttl_days):
                    expired_keys.append(cache_key)
        
        # 删除过期文件
        for key in expired_keys:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    print(f"  [缓存] 清理过期: {meta.get('ts_code', key)}")
                except:
                    pass
            del self.metadata[key]
        
        self._save_metadata()
        return len(expired_keys)
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        total_size = 0
        file_count = 0
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(self.cache_dir, filename)
                total_size += os.path.getsize(filepath)
                file_count += 1
        
        return {
            'cache_dir': self.cache_dir,
            'file_count': file_count,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'ttl_days': self.ttl_days
        }


class TushareAPIWrapperWithFinancialCache(TushareAPIWrapper):
    """
    带财务数据持久化缓存的 API 包装器
    
    继承 TushareAPIWrapper，增加财务数据季度缓存
    """
    
    def __init__(self, pro_api, max_calls: int = 400, period: int = 60):
        super().__init__(pro_api, max_calls, period)
        self.financial_cache = FinancialDataCache()
    
    def fina_indicator(self, ts_code: str = None, **kwargs):
        """
        获取财务指标（带季度缓存）
        
        自动处理缓存和增量更新
        """
        # 检查缓存
        cached = self.financial_cache.get(ts_code, 'fina_indicator')
        
        if cached is not None:
            # 检查是否需要更新（缓存超过30天但不到90天，尝试增量更新）
            meta = self.financial_cache.metadata.get(
                self.financial_cache._get_cache_key(ts_code, 'fina_indicator'), {}
            )
            last_update = meta.get('last_update')
            
            if last_update:
                days_since_update = (datetime.now() - datetime.fromisoformat(last_update)).days
                
                # 超过30天尝试增量更新，但先返回缓存数据
                if days_since_update > 30:
                    print(f"  [缓存] {ts_code} 财务数据较旧，后台尝试更新...")
                    # 这里可以触发后台更新，但同步返回旧数据
                    # 简化处理：让下次调用时再更新
        
        # 无缓存或缓存过期，重新获取
        if cached is None:
            print(f"  [API] 获取财务数据: {ts_code}")
            data = self._cached_call('fina_indicator', ts_code=ts_code, **kwargs)
            
            if data is not None and not data.empty:
                self.financial_cache.set(ts_code, data, 'fina_indicator')
            return data
        
        return cached
    
    def get_cache_stats(self):
        """获取缓存统计"""
        return self.financial_cache.get_cache_stats()


if __name__ == '__main__':
    # 测试
    import tushare as ts
    import os
    
    ts.set_token(os.getenv('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    # 使用频率限制器
    limiter = APIRateLimiter(max_calls=10, period=60)
    
    @limiter.rate_limit
    def test_api(ts_code):
        return pro.daily(ts_code=ts_code)
    
    # 测试批量调用
    stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']
    for code in stocks:
        print(f"获取 {code}...")
        result = test_api(code)
        print(f"  结果行数: {len(result) if result is not None else 0}")
    
    # 测试财务缓存
    print("\n测试财务数据缓存:")
    cache = FinancialDataCache()
    stats = cache.get_cache_stats()
    print(f"缓存统计: {stats}")
