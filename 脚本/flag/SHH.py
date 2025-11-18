import paramiko
import socket
import sys
import ipaddress

# ========== 配置参数 - 这些是需要根据实际情况修改的部分 ==========
# IP列表文件路径 - 从该文件读取目标IP地址
IP_FILE_PATH = 'ip.txt'  # 可以修改为其他文件路径
# 默认SSH服务端口 - 当IP地址不包含端口时使用
DEFAULT_SSH_PORT = 22
# SSH用户名 - 需要根据目标服务器的实际用户名修改
SSH_USERNAME = 'root'
# SSH密码 - 需要根据目标服务器的实际密码修改
SSH_PASSWORD = 'toor'
# 默认执行的命令 - 可以根据需要修改为其他命令
DEFAULT_COMMAND = 'ls'  # 例如可以修改为 'ls -la' 或 'cat /etc/passwd' 等
# ================================================================


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
                            ip_port_list.append((str(ip), DEFAULT_SSH_PORT))
                    except ValueError:
                        print(f"[-] 无效的CIDR格式: {line}")
                        continue
                # 处理纯IP格式
                else:
                    try:
                        ipaddress.ip_address(line)
                        ip_port_list.append((line, DEFAULT_SSH_PORT))
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


def ssh_connect_with_password(ip, port, username, password, cmd='ls'):
    """
    使用密码认证方式连接SSH服务器并执行命令
    
    参数:
        ip: 目标服务器的IP地址 (字符串)
        port: SSH服务端口号 (整数)
        username: SSH登录用户名 (字符串)
        password: SSH登录密码 (字符串)
        cmd: 要执行的命令，默认为'ls' (字符串)
    
    返回值:
        tuple: (success, result) - success表示是否成功，result是执行结果或错误信息
    """
    try:
        # 创建SSH客户端实例
        ssh_client = paramiko.SSHClient()
        
        # 设置自动添加主机密钥策略，避免首次连接时的确认提示
        # 注意：在生产环境中，可能需要使用更安全的主机密钥验证方式
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"[+] 正在连接 {ip}:{port}...")
        # 建立SSH连接
        ssh_client.connect(
            hostname=ip,      # 目标主机IP
            port=port,        # SSH端口
            username=username,# 用户名
            password=password,# 密码
            timeout=10        # 连接超时时间（秒）
        )
        
        print(f"[+] 连接成功，正在执行命令: {cmd}")
        # 执行命令
        stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=30)  # 命令执行超时设置
        
        # 读取命令输出
        output = stdout.read()
        
        # 如果没有输出，则尝试读取错误信息
        if not output:
            print(f"[-] {ip}:{port} 标准输出为空，尝试获取错误信息...")
            output = stderr.read()
        
        # 关闭SSH连接
        ssh_client.close()
        print(f"[+] {ip}:{port} SSH连接已关闭")
        
        # 返回解码后的输出结果
        return True, output.decode('utf-8', errors='replace')
        
    except paramiko.AuthenticationException:
        # 认证失败处理
        return False, f"[-] 认证失败: 用户名或密码错误"
    except paramiko.SSHException as e:
        # SSH连接异常处理
        return False, f"[-] SSH连接错误: {str(e)}"
    except socket.error as e:
        # 网络连接异常处理
        return False, f"[-] 网络连接错误: {str(e)}"
    except Exception as e:
        # 其他未知异常处理
        return False, f"[-] 未知错误: {str(e)}"


def main():
    """
    主函数 - 从文件读取IP地址并批量执行SSH连接
    """
    print("==== SSH批量连接工具 ====\n")
    
    # 从文件读取IP地址列表
    targets = read_ip_file(IP_FILE_PATH)
    
    if not targets:
        print("[-] 没有找到有效的目标，程序退出")
        sys.exit(1)
    
    # 统计信息
    success_count = 0
    fail_count = 0
    results = []
    
    print(f"\n[+] 开始批量执行SSH连接...")
    print(f"[+] 目标总数: {len(targets)}")
    print("=" * 60)
    
    # 对每个目标执行SSH连接
    for idx, (ip, port) in enumerate(targets, 1):
        print(f"\n[+] 处理目标 {idx}/{len(targets)}: {ip}:{port}")
        
        # 执行SSH连接和命令
        success, result = ssh_connect_with_password(
            ip=ip,
            port=port,
            username=SSH_USERNAME,
            password=SSH_PASSWORD,
            cmd=DEFAULT_COMMAND
        )
        
        # 记录结果
        if success:
            success_count += 1
            status = "成功"
        else:
            fail_count += 1
            status = "失败"
        
        results.append((ip, port, status, result))
        print(f"[+] 目标 {ip}:{port} 处理{status}")
        print("=" * 60)
    
    # 打印执行结果摘要
    print("\n==== 执行结果摘要 ====")
    print(f"总目标数: {len(targets)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print("\n详细结果:")
    
    for ip, port, status, result in results:
        print(f"\n--- {ip}:{port} ({status}) ---")
        # 限制输出长度，避免过长的结果影响阅读
        if len(result) > 500:
            print(result[:500] + "...\n[输出被截断]")
        else:
            print(result)


if __name__ == "__main__":

    main()
    
