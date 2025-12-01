#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试RSS采集器的代理配置"""
import os
import requests

print("=== 测试RSS采集代理 ===")
print(f"代理配置: {os.environ.get('http_proxy', '未设置')}")
print()

# 测试1: 国内RSS源(新智元)
print("[测试1] 访问国内RSS源(新智元)...")
try:
    url = "http://101.42.187.241:8001/feed/MP_WXS_3271041950.rss"
    response = requests.get(url, timeout=10)
    print(f"✅ 成功! 状态码: {response.status_code}, 内容长度: {len(response.content)}")
except Exception as e:
    print(f"❌ 失败: {e}")

print()

# 测试2: 国外网站
print("[测试2] 通过代理访问Google...")
try:
    response = requests.get("https://www.google.com", timeout=10)
    print(f"✅ 成功! 状态码: {response.status_code}")
except Exception as e:
    print(f"❌ 失败: {e}")
