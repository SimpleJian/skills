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
from datetime import datetime, timedelta
from typing import Callable, Any
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
