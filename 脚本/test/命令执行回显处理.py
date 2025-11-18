import importlib
import os

# 检查base64模块是否正常
try:
    base64 = importlib.import_module('base64')
    if not hasattr(base64, 'b64encode'):
        raise ImportError("base64模块不完整，缺少b64encode方法")
except ImportError as e:
    print(f"[!] base64模块错误: {e}")
    print("[!] 尝试使用替代编码方法...")
    
    # 实现简单的base64编码替代方案
    def b64encode(data):
        import binascii
        return binascii.b2a_base64(data, newline=False)
    
    class Base64替代:
        @staticmethod
        def b64encode(data):
            return b64encode(data)
    
    base64 = Base64替代

def encode_command_for_all_systems(command):
    """为Windows和类Unix系统同时生成编码命令，不执行操作"""
    results = {}
    try:
        # Windows系统处理 - 使用PowerShell的UTF-16LE编码
        win_encoded = base64.b64encode(command.encode('utf-16le')).decode()
        win_bypass = f'powershell -EncodedCommand {win_encoded}'
        
        # Unix/Linux系统处理 - 使用UTF-8编码和${IFS}绕过
        unix_encoded = base64.b64encode(command.encode()).decode()
        unix_bypass = f"echo${{IFS}}{unix_encoded}|base64${{IFS}}-d|sh"
        
        results = {
            "success": True,
            "original_command": command,
            "windows": {
                "encoded_command": win_encoded,
                "bypass_command": win_bypass,
                "encoding": "UTF-16LE"
            },
            "unix_linux": {
                "encoded_command": unix_encoded,
                "bypass_command": unix_bypass,
                "encoding": "UTF-8"
            }
        }
        
    except Exception as e:
        results = {
            "success": False,
            "error": str(e)
        }
        
    return results

if __name__ == "__main__":
    print("===== 多系统命令编码工具 (仅编码不执行) =====")
    print("提示: 输入命令进行编码，输入 'exit' 退出程序")
    print("将同时显示Windows和Unix/Linux系统的编码结果")
    print("-"*30)
    
    while True:
        try:
            cmd = input("\n请输入要编码的命令: ").strip()
            
            if cmd.lower() == 'exit':
                print("程序已退出")
                break
                
            if not cmd:
                continue
                
            print("\n" + "="*70)
            print(f"[+] 原始命令: {cmd}")
            print("-"*70)
            
            result = encode_command_for_all_systems(cmd)
            
            if result["success"]:
                # 显示Windows系统结果
                print("\n[+] Windows系统适配:")
                print(f"    编码方式: {result['windows']['encoding']}")
                print(f"    Base64编码: {result['windows']['encoded_command']}")
                print(f"    执行命令: {result['windows']['bypass_command']}")
                
                # 显示Unix/Linux系统结果
                print("\n[+] Unix/Linux系统适配:")
                print(f"    编码方式: {result['unix_linux']['encoding']}")
                print(f"    Base64编码: {result['unix_linux']['encoded_command']}")
                print(f"    执行命令: {result['unix_linux']['bypass_command']}")
            else:
                print("[-] 编码失败!")
                print(f"[-] 错误信息: {result['error']}")
                
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")
    