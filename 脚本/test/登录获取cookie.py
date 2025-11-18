import requests
import ipaddress
import sys
import os
from datetime import datetime

# ========== 配置参数 ==========
# IP列表文件路径
IP_FILE_PATH = 'ip.txt'
# Cookie保存文件路径
COOKIE_FILE_PATH = 'cookie.txt'
# 默认端口 (当IP地址不包含端口时使用)
DEFAULT_PORT = 80
# 默认路径 (登录页面路径)
DEFAULT_PATH = '/index.php'
# 默认协议
DEFAULT_PROTOCOL = 'http'
# 超时设置 (秒)
TIMEOUT = 30
# 登录账号密码
LOGIN_DATA = {
    'username': 'admin',  # 修改为实际的用户名
    'password': 'password',  # 修改为实际的密码
    'submit': 'login'  # 登录按钮的name属性
}
# 自定义请求头
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}
# ========== 配置参数结束 ==========

def init_cookie_file():
    """
    初始化cookie.txt文件，清空旧内容并写入标题
    """
    try:
        with open(COOKIE_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(f"# Cookie信息收集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# 格式: IP:端口 | cookie\n\n")
        print(f"[+] 已初始化 {COOKIE_FILE_PATH}")
        return True
    except Exception as e:
        print(f"[-] 初始化Cookie文件失败: {str(e)}")
        return False

def read_ip_file(file_path):
    """
    读取IP地址文件并解析不同格式的地址
    
    支持的格式:
    - IP:端口格式 (如 8.148.182.33:8805)
    - 纯IP格式 (如 8.148.182.34)，会使用默认端口
    - CIDR格式 (如 8.148.182.35/30)，会解析出所有包含的IP地址
    
    参数:
        file_path: IP地址文件路径
    
    返回值:
        list: [(ip, port)] 格式的列表，包含所有解析出的IP和端口组合
    """
    ip_port_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  # 跳过空行和注释行
                
                # 处理带端口的IP格式
                if ':' in line and not '/' in line:
                    ip, port = line.split(':', 1)
                    try:
                        # 验证IP格式并将端口转换为整数
                        ipaddress.ip_address(ip)
                        port = int(port)
                        ip_port_list.append((ip, port))
                    except (ipaddress.AddressValueError, ValueError):
                        print(f"[-] 无效的IP:端口格式: {line}")
                        continue
                # 处理CIDR格式
                elif '/' in line:
                    try:
                        network = ipaddress.ip_network(line, strict=False)
                        # 为CIDR范围内的每个IP添加默认端口
                        for ip in network.hosts():
                            ip_port_list.append((str(ip), DEFAULT_PORT))
                    except ValueError:
                        print(f"[-] 无效的CIDR格式: {line}")
                        continue
                # 处理纯IP格式
                else:
                    try:
                        ipaddress.ip_address(line)
                        ip_port_list.append((line, DEFAULT_PORT))
                    except ipaddress.AddressValueError:
                        print(f"[-] 无效的IP地址: {line}")
                        continue
        
        print(f"[+] 从 {file_path} 成功读取 {len(ip_port_list)} 个目标")
        return ip_port_list
        
    except FileNotFoundError:
        print(f"[-] 错误: 找不到文件 {file_path}")
        return []
    except Exception as e:
        print(f"[-] 读取IP文件时出错: {str(e)}")
        return []

def get_cookie_string(cookies):
    """
    将cookies字典转换为字符串格式
    
    参数:
        cookies: cookies字典
    
    返回值:
        str: cookie字符串，格式为"name1=value1; name2=value2;"
    """
    cookie_strings = []
    for name, value in cookies.items():
        cookie_strings.append(f"{name}={value}")
    return "; ".join(cookie_strings)

def save_cookie_to_file(ip, port, cookie_string):
    """
    将cookie信息保存到cookie.txt文件中
    格式: IP:端口 | cookie
    
    参数:
        ip: 目标IP
        port: 目标端口
        cookie_string: cookie字符串
    """
    try:
        with open(COOKIE_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{ip}:{port} | {cookie_string}\n")
        print(f"[+] 已保存cookie到 {COOKIE_FILE_PATH}")
        return True
    except Exception as e:
        print(f"[-] 保存cookie文件失败: {str(e)}")
        return False

def send_login_request(ip, port):
    """
    发送登录POST请求并获取cookie
    
    参数:
        ip: 目标IP地址
        port: 目标端口
    
    返回值:
        tuple: (success, cookie_string/error_msg)
    """
    # 构建完整的URL
    url = f"{DEFAULT_PROTOCOL}://{ip}:{port}{DEFAULT_PATH}"
    print(f"\n[+] 发送登录请求到: {url}")
    print(f"[+] 用户名: {LOGIN_DATA.get('username')}")
    
    try:
        # 发送POST登录请求
        response = requests.post(
            url,
            data=LOGIN_DATA,
            headers=CUSTOM_HEADERS,
            timeout=TIMEOUT,
            allow_redirects=False
        )
        
        # 输出响应状态码
        print(f"[+] 响应状态码: {response.status_code}")
        
        # 获取Cookie
        if hasattr(response, 'cookies') and response.cookies:
            cookie_string = get_cookie_string(dict(response.cookies))
            print(f"[+] 获取到Cookie: {cookie_string}")
            return True, cookie_string
        else:
            print("[+] 未获取到Cookie信息")
            return False, "无Cookie"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"请求失败: {str(e)}"
        print(f"[-] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        print(f"[-] {error_msg}")
        return False, error_msg

def main():
    """
    主函数 - 批量登录获取cookie
    """
    print("==== POST登录获取Cookie工具 ====\n")
    print("功能说明：")
    print("1. 支持从ip.txt读取目标IP和端口")
    print("2. 发送POST登录请求并提取Cookie信息")
    print("3. 按行格式保存Cookie到cookie.txt文件")
    print("4. 格式: IP:端口 | cookie\n")
    
    # 初始化cookie文件
    if not init_cookie_file():
        print("[-] Cookie文件初始化失败，程序退出")
        sys.exit(1)
    
    # 从文件读取IP地址列表
    targets = read_ip_file(IP_FILE_PATH)
    
    if not targets:
        print("[-] 没有找到有效的目标，程序退出")
        sys.exit(1)
    
    # 统计信息
    success_count = 0
    fail_count = 0
    cookie_count = 0
    
    print(f"[+] 开始批量登录获取Cookie...")
    print(f"[+] 目标总数: {len(targets)}")
    print("=" * 60)
    
    # 对每个目标执行登录请求
    for idx, (ip, port) in enumerate(targets, 1):
        print(f"\n[+] 处理目标 {idx}/{len(targets)}: {ip}:{port}")
        
        # 发送登录请求
        success, result = send_login_request(ip, port)
        
        # 保存到文件
        save_cookie_to_file(ip, port, result)
        
        # 更新统计信息
        if success:
            success_count += 1
            cookie_count += 1
        else:
            fail_count += 1
        
        print("=" * 60)
    
    # 打印执行结果摘要
    print("\n==== 执行结果摘要 ====")
    print(f"总目标数: {len(targets)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"获取Cookie数: {cookie_count}")
    print(f"Cookie文件: {COOKIE_FILE_PATH}")


if __name__ == "__main__":
    main()
    
    # 配置说明：
    # 1. 修改LOGIN_DATA字典以设置正确的登录账号密码
    # 2. 修改DEFAULT_PATH以指定正确的登录页面路径
    # 3. 根据需要调整CUSTOM_HEADERS中的请求头信息
    # 4. cookie.txt文件格式: IP:端口 | cookie