import os
import re
import requests
from datetime import datetime

# ========== 配置参数 ==========
# 响应文件目录
RESPONSES_DIR = 'responses'
# Flag上传URL
FLAG_UPLOAD_URL = 'http://8.148.182.33:8080/flag_file.php'
# 团队Token
TEAM_TOKEN = 'team5'
# 上传方式: 'GET' 或 'POST'
UPLOAD_METHOD = 'GET'  # 可以更改为 'POST'
# 超时设置 (秒)
TIMEOUT = 30
# 自定义请求头
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}
# Flag提取正则表达式模式列表
FLAG_PATTERNS = [
    r'flag\{([^\}]*)\}',  # flag{...} 格式
    r'FLAG\{([^\}]*)\}',  # FLAG{...} 格式
    r'flag=([a-zA-Z0-9]{32})',  # flag=32位字符 格式
    r'FLAG=([a-zA-Z0-9]{32})',  # FLAG=32位字符 格式
    r'[a-zA-Z0-9]{32}',  # 32位字符（可能是MD5）
    r'[a-zA-Z0-9]{64}',  # 64位字符（可能是SHA256）
    r'[a-zA-Z0-9]{40}',  # 40位字符（可能是SHA1）
]
# ========== 配置参数结束 ==========

def find_response_files(directory):
    """
    查找响应目录中的所有文本文件
    
    参数:
        directory: 目录路径
    
    返回值:
        list: 文件路径列表
    """
    file_paths = []
    
    try:
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                file_path = os.path.join(directory, filename)
                file_paths.append(file_path)
        
        print(f"[+] 在 {directory} 中找到 {len(file_paths)} 个响应文件")
        return file_paths
        
    except FileNotFoundError:
        print(f"[-] 错误: 找不到目录 {directory}")
        return []
    except Exception as e:
        print(f"[-] 查找文件时出错: {str(e)}")
        return []

def extract_flags_from_file(file_path):
    """
    从响应文件中提取flag信息
    
    参数:
        file_path: 文件路径
    
    返回值:
        list: 提取到的flag列表
    """
    flags = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # 尝试每种flag模式
            for pattern in FLAG_PATTERNS:
                matches = re.findall(pattern, content)
                for match in matches:
                    # 对于有分组的模式，取分组内容；否则取整个匹配
                    flag_value = match if isinstance(match, str) else match[0]
                    # 处理完整格式的flag
                    if pattern.startswith(r'flag\{') or pattern.startswith(r'FLAG\{'):
                        full_flag = pattern.split(r'\{')[0] + '{' + flag_value + '}'
                        if full_flag not in flags:
                            flags.append(full_flag)
                    else:
                        # 对于简单格式，直接添加
                        if flag_value not in flags:
                            flags.append(flag_value)
        
        if flags:
            print(f"[+] 从 {os.path.basename(file_path)} 中提取到 {len(flags)} 个可能的flag")
            for flag in flags:
                print(f"    - {flag}")
        else:
            print(f"[-] 从 {os.path.basename(file_path)} 中未提取到flag")
        
        return flags
        
    except Exception as e:
        print(f"[-] 读取文件 {file_path} 时出错: {str(e)}")
        return []

def upload_flag(flag):
    """
    上传flag到服务器
    
    参数:
        flag: flag值
    
    返回值:
        dict: 上传结果 {success: bool, response: str, status_code: int}
    """
    print(f"\n[+] 上传flag: {flag}")
    
    # 准备请求参数
    params = {
        'token': TEAM_TOKEN,
        'flag': flag
    }
    
    try:
        if UPLOAD_METHOD.upper() == 'GET':
            # 使用GET方法上传
            print(f"[+] 使用GET方法上传到: {FLAG_UPLOAD_URL}")
            response = requests.get(
                FLAG_UPLOAD_URL,
                params=params,
                headers=CUSTOM_HEADERS,
                timeout=TIMEOUT,
                allow_redirects=False
            )
        else:
            # 使用POST方法上传
            print(f"[+] 使用POST方法上传到: {FLAG_UPLOAD_URL}")
            response = requests.post(
                FLAG_UPLOAD_URL,
                data=params,
                headers=CUSTOM_HEADERS,
                timeout=TIMEOUT,
                allow_redirects=False
            )
        
        # 获取响应内容
        response_text = response.text.strip()
        print(f"[+] 响应状态码: {response.status_code}")
        print(f"[+] 响应内容: {response_text}")
        
        # 判断上传是否成功（根据响应内容）
        success_keywords = ['success', '成功', 'ok', 'OK', 'accepted']
        failure_keywords = ['error', '失败', 'invalid', 'no such', 'not found']
        
        is_success = False
        for keyword in success_keywords:
            if keyword.lower() in response_text.lower():
                is_success = True
                break
                
        for keyword in failure_keywords:
            if keyword.lower() in response_text.lower():
                is_success = False
                break
                
        return {
            'success': is_success,
            'response': response_text,
            'status_code': response.status_code
        }
        
    except requests.exceptions.RequestException as e:
        error_msg = f"请求失败: {str(e)}"
        print(f"[-] {error_msg}")
        return {
            'success': False,
            'response': error_msg,
            'status_code': None
        }
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        print(f"[-] {error_msg}")
        return {
            'success': False,
            'response': error_msg,
            'status_code': None
        }

def main():
    """
    主函数 - 从响应文件中提取flag并上传
    """
    print("==== Flag提取与上传工具 ====\n")
    print("功能说明：")
    print("1. 扫描responses目录中的响应文件")
    print("2. 提取可能的flag信息")
    print("3. 上传flag到指定服务器")
    print(f"4. 使用{UPLOAD_METHOD}方法上传到: {FLAG_UPLOAD_URL}\n")
    
    # 查找所有响应文件
    response_files = find_response_files(RESPONSES_DIR)
    
    if not response_files:
        print("[-] 没有找到响应文件，程序退出")
        return
    
    # 统计信息
    total_files = len(response_files)
    processed_files = 0
    total_flags_extracted = 0
    unique_flags = set()
    total_uploaded = 0
    upload_success_count = 0
    upload_fail_count = 0
    
    print(f"[+] 开始提取和上传flag...")
    print("=" * 60)
    
    # 处理每个响应文件
    for file_path in response_files:
        processed_files += 1
        print(f"\n[+] 处理文件 {processed_files}/{total_files}: {os.path.basename(file_path)}")
        
        # 提取flag
        flags = extract_flags_from_file(file_path)
        total_flags_extracted += len(flags)
        
        # 去重并上传
        for flag in flags:
            if flag not in unique_flags:
                unique_flags.add(flag)
                
                # 上传flag
                result = upload_flag(flag)
                total_uploaded += 1
                
                if result['success']:
                    upload_success_count += 1
                else:
                    upload_fail_count += 1
        
        print("=" * 60)
    
    # 打印执行结果摘要
    print("\n==== 执行结果摘要 ====")
    print(f"总响应文件数: {total_files}")
    print(f"提取的flag总数: {total_flags_extracted}")
    print(f"去重后的flag数: {len(unique_flags)}")
    print(f"上传总次数: {total_uploaded}")
    print(f"上传成功: {upload_success_count}")
    print(f"上传失败: {upload_fail_count}")
    print(f"上传URL: {FLAG_UPLOAD_URL}")
    print(f"上传方法: {UPLOAD_METHOD}")
    print(f"团队Token: {TEAM_TOKEN}")
    
    # 列出上传的唯一flag
    if unique_flags:
        print("\n上传的唯一flag列表:")
        for i, flag in enumerate(unique_flags, 1):
            print(f"  {i}. {flag}")


if __name__ == "__main__":
    main()
    
    # 配置说明：
    # 1. 修改TEAM_TOKEN为实际的团队token
    # 2. 根据需要修改UPLOAD_METHOD为'GET'或'POST'
    # 3. 可以在FLAG_PATTERNS中添加更多的flag匹配模式
    # 4. 调整TIMEOUT以适应网络环境