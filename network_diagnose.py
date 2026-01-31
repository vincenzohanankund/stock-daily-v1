# -*- coding: utf-8 -*-
"""
网络诊断脚本 - 检查 Python 程序的网络连接状态
"""
import os
import sys
import socket
import ssl
import requests
from urllib.request import getproxies

# 设置控制台编码为 UTF-8（Windows）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def check_proxy_settings():
    """检查系统代理设置"""
    print_section("1. 系统代理检查")
    
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
    found_proxy = False
    
    print("\n环境变量中的代理设置:")
    for var in proxy_vars:
        value = os.getenv(var, '')
        if value:
            print(f"  {var} = {value}")
            found_proxy = True
        else:
            print(f"  {var} = (未设置)")
    
    print("\nurllib 自动检测到的代理:")
    proxies = getproxies()
    if proxies:
        for key, value in proxies.items():
            print(f"  {key} = {value}")
        found_proxy = True
    else:
        print("  (未检测到代理)")
    
    if not found_proxy:
        print("\n[INFO] 未检测到系统代理设置")
    else:
        print("\n[INFO] 检测到代理设置")

def test_connectivity(url, name, timeout=5):
    """测试网络连通性"""
    print(f"\n测试: {name}")
    print(f"  URL: {url}")
    
    try:
        # 尝试解析域名
        hostname = url.replace('https://', '').replace('http://', '').split('/')[0]
        print(f"  解析域名: {hostname}")
        
        # DNS 解析测试
        try:
            ip = socket.gethostbyname(hostname)
            print(f"  DNS 解析成功: {ip}")
        except socket.gaierror as e:
            print(f"  [ERROR] DNS 解析失败: {e}")
            return False
        
        # HTTP 请求测试
        response = requests.get(url, timeout=timeout, allow_redirects=True)
        print(f"  [OK] 连接成功!")
        print(f"  状态码: {response.status_code}")
        print(f"  响应时间: {response.elapsed.total_seconds():.2f} 秒")
        return True
        
    except requests.exceptions.Timeout:
        print(f"  [ERROR] 连接超时 (>{timeout}秒)")
        return False
    except requests.exceptions.SSLError as e:
        print(f"  [ERROR] SSL 证书错误: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"  [ERROR] 连接失败: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] 请求异常: {type(e).__name__}: {e}")
        return False
    except Exception as e:
        print(f"  [ERROR] 未知错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_connectivity(hostname, port=443, timeout=5):
    """测试 API 连通性（TCP 连接）"""
    print(f"\n测试: {hostname}:{port}")
    
    try:
        # 创建 socket 连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"  [OK] TCP 连接成功!")
            return True
        else:
            print(f"  [ERROR] TCP 连接失败 (错误码: {result})")
            return False
            
    except socket.gaierror as e:
        print(f"  [ERROR] DNS 解析失败: {e}")
        return False
    except socket.timeout:
        print(f"  [ERROR] 连接超时 (>{timeout}秒)")
        return False
    except Exception as e:
        print(f"  [ERROR] 连接异常: {type(e).__name__}: {e}")
        return False

def test_ssl_connection(hostname, port=443, timeout=5):
    """测试 SSL 连接"""
    print(f"\n测试 SSL 连接: {hostname}:{port}")
    
    try:
        # 创建 socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((hostname, port))
        
        # 创建 SSL 上下文
        context = ssl.create_default_context()
        ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
        
        # 获取证书信息
        cert = ssl_sock.getpeercert()
        print(f"  [OK] SSL 握手成功!")
        print(f"  证书主题: {cert.get('subject', 'N/A')}")
        print(f"  证书颁发者: {cert.get('issuer', 'N/A')}")
        
        ssl_sock.close()
        return True
        
    except ssl.SSLError as e:
        print(f"  [ERROR] SSL 错误: {e}")
        return False
    except socket.gaierror as e:
        print(f"  [ERROR] DNS 解析失败: {e}")
        return False
    except socket.timeout:
        print(f"  [ERROR] 连接超时 (>{timeout}秒)")
        return False
    except Exception as e:
        print(f"  [ERROR] SSL 连接异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print(" Python 网络诊断工具")
    print("=" * 60)
    
    # 1. 检查代理设置
    check_proxy_settings()
    
    # 2. 基础连通性测试
    print_section("2. 基础连通性测试")
    results = {}
    
    results['baidu'] = test_connectivity('https://www.baidu.com', '百度 (国内网络)')
    results['google'] = test_connectivity('https://www.google.com', 'Google (翻墙网络)')
    results['github'] = test_connectivity('https://github.com', 'GitHub')
    
    # 3. API 连通性测试
    print_section("3. API 连通性测试")
    
    # Gemini API 域名
    gemini_host = 'generativelanguage.googleapis.com'
    results['gemini_tcp'] = test_api_connectivity(gemini_host, 443)
    results['gemini_ssl'] = test_ssl_connection(gemini_host, 443)
    
    # 尝试 HTTP 请求（可能会返回 404/403，但说明能连接）
    print(f"\n测试: Gemini API HTTP 请求")
    print(f"  URL: https://{gemini_host}/")
    try:
        response = requests.get(f'https://{gemini_host}/', timeout=5)
        print(f"  [OK] HTTP 请求成功!")
        print(f"  状态码: {response.status_code}")
        results['gemini_http'] = True
    except requests.exceptions.SSLError as e:
        print(f"  [ERROR] SSL 错误: {e}")
        results['gemini_http'] = False
    except requests.exceptions.ConnectionError as e:
        print(f"  [ERROR] 连接失败: {e}")
        results['gemini_http'] = False
    except Exception as e:
        print(f"  [ERROR] 请求异常: {type(e).__name__}: {e}")
        results['gemini_http'] = False
    
    # 4. 总结和建议
    print_section("4. 诊断总结")
    
    print("\n测试结果汇总:")
    print(f"  百度连接: {'[OK]' if results.get('baidu') else '[FAIL]'}")
    print(f"  Google连接: {'[OK]' if results.get('google') else '[FAIL]'}")
    print(f"  GitHub连接: {'[OK]' if results.get('github') else '[FAIL]'}")
    print(f"  Gemini TCP: {'[OK]' if results.get('gemini_tcp') else '[FAIL]'}")
    print(f"  Gemini SSL: {'[OK]' if results.get('gemini_ssl') else '[FAIL]'}")
    print(f"  Gemini HTTP: {'[OK]' if results.get('gemini_http') else '[FAIL]'}")
    
    print("\n建议:")
    if not results.get('baidu'):
        print("  [WARN] 无法连接百度，基础网络可能有问题")
    
    if not results.get('google') and not results.get('github'):
        print("  [WARN] 无法连接 Google/GitHub，可能需要配置代理或 VPN")
    
    if not results.get('gemini_tcp'):
        print("  [WARN] 无法连接到 Gemini API 服务器，请检查:")
        print("    - 网络连接是否正常")
        print("    - 是否需要配置代理")
        print("    - 防火墙是否阻止了连接")
    
    if not results.get('gemini_ssl'):
        print("  [WARN] Gemini API SSL 握手失败，可能是:")
        print("    - SSL 证书问题")
        print("    - 代理配置问题")
        print("    - 系统时间不正确")
    
    if results.get('gemini_tcp') and results.get('gemini_ssl'):
        print("  [OK] Gemini API 连接正常，可以正常使用!")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
    except Exception as e:
        print(f"\n[ERROR] 程序异常: {e}")
        import traceback
        traceback.print_exc()
