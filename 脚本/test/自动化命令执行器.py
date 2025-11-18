#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级自动化循环执行命令脚本 V2.0
适用于AWD竞赛环境中的命令自动化执行
"""

import os
import sys
import time
import json
import subprocess
import threading
import logging
import schedule
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# 配置日志
# 日志格式化器将在后面定义，使用安全的方式处理中文输出

# 创建日志配置
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"command_executor_{datetime.now().strftime('%Y%m%d')}.log")

# 创建logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 清除已有的处理器（避免重复）
logger.handlers.clear()

# 文件处理器 - 使用严格的编码处理
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# 控制台处理器 - Windows环境下特殊处理
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 为Windows环境定制日志格式化器
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # 处理消息中的编码问题
        try:
            # 确保消息是字符串
            if not isinstance(record.msg, str):
                record.msg = str(record.msg)
            
            # 对于Windows系统，尝试使用cp936编码输出
            if sys.platform.startswith('win'):
                # 先尝试直接格式化
                try:
                    return super().format(record)
                except UnicodeEncodeError:
                    # 如果失败，替换非ASCII字符
                    record.msg = ''.join(c if ord(c) < 128 or (0x4e00 <= ord(c) <= 0x9fff) else '?' for c in record.msg)
            return super().format(record)
        except Exception:
            # 最极端情况下的保障
            return f"{record.asctime} - {record.levelname} - [无法格式化的消息]"

console_formatter = SafeFormatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 避免Windows环境下的颜色代码问题
if not sys.platform.startswith('win'):
    # 只有非Windows系统使用颜色
    class ColoredFormatter(SafeFormatter):
        """带颜色的日志格式化器"""
        COLORS = {
            'DEBUG': '\033[36m',      # 青色
            'INFO': '\033[32m',       # 绿色
            'WARNING': '\033[33m',    # 黄色
            'ERROR': '\033[31m',      # 红色
            'CRITICAL': '\033[35m',   # 紫色
            'RESET': '\033[0m'        # 重置
        }
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            
            # 为日志级别添加颜色
            record.levelname = f"{color}{record.levelname}{reset}"
            return super().format(record)
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

console_handler.setFormatter(console_formatter)

# 添加处理器到logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class CommandExecutor:
    """高级命令自动执行器"""
    def __init__(self):
        self.command_groups = {"default": []}  # 命令分组
        self.active_groups = ["default"]  # 激活的命令组
        self.interval = 60  # 默认执行间隔（秒）
        self.is_running = False
        self.is_paused = False
        self.execution_count = 0
        self.last_execution = None
        self.schedule_tasks = []  # 定时任务列表
        self.lock = threading.RLock()  # 线程锁
        self.thread = None
        self.monitoring_rules = {}  # 监控规则
        self.max_workers = 3  # 并发执行的最大线程数
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.execution_history = []  # 执行历史
        self.history_limit = 100  # 历史记录限制
        
    def load_config(self):
        """从配置文件加载设置"""
        config_file = 'command_config.txt'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    current_group = "default"
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if line.startswith('[') and line.endswith(']'):
                            # 命令分组
                            current_group = line[1:-1]
                            if current_group not in self.command_groups:
                                self.command_groups[current_group] = []
                            logger.info(f"创建命令分组: {current_group}")
                        elif line.startswith('INTERVAL='):
                            try:
                                self.interval = int(line.split('=', 1)[1])
                                logger.info(f"从配置加载执行间隔: {self.interval}秒")
                            except ValueError:
                                logger.error(f"无效的间隔配置: {line}")
                        elif line.startswith('SCHEDULE='):
                            # 定时任务配置
                            schedule_config = line.split('=', 1)[1]
                            self.schedule_tasks.append(schedule_config)
                            logger.info(f"添加定时任务: {schedule_config}")
                        elif line.startswith('MONITOR_'):
                            # 监控规则配置
                            rule_name, rule_value = line.split('=', 1)
                            self.monitoring_rules[rule_name[8:]] = rule_value
                            logger.info(f"添加监控规则: {rule_name[8:]}={rule_value}")
                        else:
                            # 普通命令
                            self.command_groups[current_group].append(line)
                            logger.info(f"在分组 {current_group} 添加命令: {line}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        
        # 清理空分组
        self.command_groups = {k: v for k, v in self.command_groups.items() if v}
        
        # 如果默认分组为空，添加默认命令
        if "default" not in self.command_groups or not self.command_groups["default"]:
            self.command_groups["default"] = [
                'echo "自动执行命令示例"',
                'dir' if sys.platform.startswith('win') else 'ls -la'
            ]
            logger.info("使用默认命令列表")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open('command_config.txt', 'w', encoding='utf-8') as f:
                f.write(f"# AWD自动化命令执行器配置文件\n")
                f.write(f"# 最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 保存执行间隔
                f.write(f"INTERVAL={self.interval}\n\n")
                
                # 保存定时任务
                for task in self.schedule_tasks:
                    f.write(f"SCHEDULE={task}\n")
                if self.schedule_tasks:
                    f.write("\n")
                
                # 保存监控规则
                for rule_name, rule_value in self.monitoring_rules.items():
                    f.write(f"MONITOR_{rule_name}={rule_value}\n")
                if self.monitoring_rules:
                    f.write("\n")
                
                # 保存命令分组
                for group_name, commands in self.command_groups.items():
                    f.write(f"[{group_name}]\n")
                    for cmd in commands:
                        f.write(f"{cmd}\n")
                    f.write("\n")
            
            logger.info("配置已保存到command_config.txt")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def execute_command(self, cmd):
        """执行单个命令，支持实时输出和编码处理"""
        start_time = time.time()
        logger.info(f"开始执行命令: {cmd}")
        
        try:
            # 根据平台选择shell类型
            shell = True if sys.platform.startswith('win') else False
            
            # 为Windows环境配置编码环境变量
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # 执行命令
            process = subprocess.Popen(
                cmd if sys.platform.startswith('win') else cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=shell,
                env=env
            )
            
            # 实时输出
            stdout_lines = []
            stderr_lines = []
            
            # 读取标准输出
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    clean_line = self._clean_output(line.strip())
                    logger.info(f"[输出] {clean_line}")
                    stdout_lines.append(clean_line)
            
            # 读取标准错误
            for line in iter(process.stderr.readline, ''):
                if line.strip():
                    clean_line = self._clean_output(line.strip())
                    logger.error(f"[错误] {clean_line}")
                    stderr_lines.append(clean_line)
            
            # 等待进程完成
            process.wait()
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 记录执行结果
            result = {
                "command": cmd,
                "returncode": process.returncode,
                "stdout": stdout_lines,
                "stderr": stderr_lines,
                "execution_time": round(execution_time, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            # 检查监控规则
            self._check_monitoring_rules(result)
            
            # 保存到历史记录
            self._add_to_history(result)
            
            if process.returncode == 0:
                logger.info(f"命令执行成功: {cmd} (耗时: {execution_time:.2f}秒)")
            else:
                logger.warning(f"命令执行失败，返回码: {process.returncode}, 命令: {cmd} (耗时: {execution_time:.2f}秒)")
            
            return result
            
        except Exception as e:
            error_msg = f"执行命令时发生异常: {str(e)}"
            logger.error(error_msg)
            return {
                "command": cmd,
                "returncode": -1,
                "stdout": [],
                "stderr": [error_msg],
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _clean_output(self, output):
        """清理输出，确保中文显示正常"""
        try:
            # 处理None值
            if output is None:
                return ""
                
            # 处理bytes类型
            if isinstance(output, bytes):
                # Windows环境特殊处理编码问题
                encodings_to_try = ['cp936', 'utf-8', 'gb2312', 'gbk', 'latin1']
                decoded_output = None
                
                for encoding in encodings_to_try:
                    try:
                        decoded_output = output.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                # 如果所有编码都失败，使用latin1作为最后手段
                if decoded_output is None:
                    try:
                        decoded_output = output.decode('latin1')
                    except:
                        decoded_output = "[解码失败]"
                
                output = decoded_output
            
            # 确保是字符串类型
            elif not isinstance(output, str):
                output = str(output)
                
            # 移除控制字符，但保留换行、制表符和回车符
            clean_output = ''
            for char in output:
                # 保留换行符、制表符、回车符、可打印ASCII字符和中文字符
                if char in ('\n', '\t', '\r') or 32 <= ord(char) <= 126 or (0x4e00 <= ord(char) <= 0x9fff):
                    clean_output += char
                # 对于其他控制字符，用空格替换
                elif ord(char) < 32:
                    clean_output += ' ' 
            
            # Windows环境下的编码处理增强
            if sys.platform.startswith('win'):
                # 对于Windows，优先尝试cp936(GBK)编码处理
                try:
                    return clean_output.encode('utf-8', errors='replace').decode('cp936', errors='replace')
                except Exception:
                    # 如果失败，尝试多种编码组合
                    encodings = ['utf-8', 'cp936', 'gb18030', 'iso-8859-1']
                    for encoding in encodings:
                        try:
                            return clean_output.encode(encoding, errors='replace').decode(encoding, errors='replace')
                        except Exception:
                            continue
            
            # 非Windows环境使用UTF-8
            try:
                return clean_output.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            except Exception:
                # 最终保障 - 保留中文和基本ASCII
                return ''.join(c if ord(c) < 128 or c in '\n\t\r' or (0x4e00 <= ord(c) <= 0x9fff) else '?' for c in clean_output)
                
        except Exception as e:
            logger.debug(f"清理输出时出错: {str(e)}")
            # 最基础的保障
            return str(output) if output else ""
    
    def _safe_print(self, text):
        """安全打印函数，处理各种编码问题"""
        try:
            print(text)
        except UnicodeEncodeError:
            # 尝试替换不可打印字符
            safe_text = ''.join(c if ord(c) < 128 or c in '\n\t\r' or (0x4e00 <= ord(c) <= 0x9fff) else '?' for c in text)
            print(safe_text)
        except Exception as e:
            logger.error(f"打印输出时出错: {str(e)}")
    
    def _check_monitoring_rules(self, result):
        """检查监控规则并报警"""
        if not self.monitoring_rules:
            return
        
        # 检查关键字
        if "contains" in self.monitoring_rules:
            keywords = [k.strip() for k in self.monitoring_rules["contains"].split(',')]
            all_output = '\n'.join(result["stdout"] + result["stderr"])
            
            for keyword in keywords:
                if keyword in all_output:
                    logger.warning(f"⚠️  监控告警: 在命令 '{result['command']}' 的输出中发现关键字 '{keyword}'")
        
        # 检查返回码
        if "returncode" in self.monitoring_rules:
            expected_codes = [int(c.strip()) for c in self.monitoring_rules["returncode"].split(',')]
            if result["returncode"] not in expected_codes:
                logger.warning(f"⚠️  监控告警: 命令 '{result['command']}' 返回码 {result['returncode']} 不在预期列表 {expected_codes} 中")
        
        # 检查执行时间
        if "max_time" in self.monitoring_rules:
            try:
                max_time = float(self.monitoring_rules["max_time"])
                if result["execution_time"] > max_time:
                    logger.warning(f"⚠️  监控告警: 命令 '{result['command']}' 执行时间 {result['execution_time']:.2f}秒 超过最大限制 {max_time}秒")
            except ValueError:
                pass
    
    def _add_to_history(self, result):
        """添加执行结果到历史记录"""
        with self.lock:
            self.execution_history.append(result)
            # 限制历史记录数量
            if len(self.execution_history) > self.history_limit:
                self.execution_history = self.execution_history[-self.history_limit:]
    
    def run_cycle(self):
        """执行一个完整的命令循环"""
        with self.lock:
            self.execution_count += 1
            self.last_execution = datetime.now()
            logger.info(f"\n开始第 {self.execution_count} 轮命令执行 - {self.last_execution.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 执行所有激活组的命令
        commands_to_execute = []
        with self.lock:
            for group in self.active_groups:
                if group in self.command_groups:
                    commands_to_execute.extend(self.command_groups[group])
        
        # 执行命令（可选择并发或顺序）
        results = []
        for cmd in commands_to_execute:
            if not self.is_running:
                break
                
            # 检查暂停状态
            while self.is_paused:
                if not self.is_running:
                    break
                time.sleep(1)
            
            if not self.is_running:
                break
                
            # 执行命令并获取结果
            result = self.execute_command(cmd)
            results.append(result)
        
        # 记录本轮执行统计
        if results:
            success_count = sum(1 for r in results if r["returncode"] == 0)
            total_time = sum(r["execution_time"] for r in results)
            logger.info(f"\n第 {self.execution_count} 轮执行统计:")
            logger.info(f"  命令总数: {len(results)}")
            logger.info(f"  成功数量: {success_count}")
            logger.info(f"  失败数量: {len(results) - success_count}")
            logger.info(f"  总耗时: {total_time:.2f}秒")
            logger.info(f"====================================\n")
    
    def start(self):
        """启动自动执行"""
        with self.lock:
            if self.is_running:
                logger.warning("自动执行器已经在运行")
                return False
            
            self.is_running = True
            self.is_paused = False
            logger.info(f"启动自动执行器，执行间隔: {self.interval}秒")
            logger.info(f"激活的命令组: {self.active_groups}")
            
            # 初始化定时任务
            self._setup_scheduled_tasks()
        
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def _run_loop(self):
        """主循环线程"""
        try:
            while self.is_running:
                # 执行命令循环
                self.run_cycle()
                
                # 等待下一轮执行
                wait_time = self.interval
                next_run = datetime.now() + timedelta(seconds=wait_time)
                
                while wait_time > 0 and self.is_running:
                    # 检查定时任务
                    schedule.run_pending()
                    
                    # 暂停检查
                    if not self.is_paused:
                        wait_time -= 1
                        logger.debug(f"距离下次执行还有 {wait_time} 秒...")
                    else:
                        logger.debug("执行已暂停")
                    
                    time.sleep(1)
                    
        except Exception as e:
            logger.error(f"主循环发生异常: {str(e)}")
        finally:
            with self.lock:
                self.is_running = False
                self.is_paused = False
            logger.info("自动执行器已停止")
    
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        # 清除现有任务
        schedule.clear()
        
        for task_config in self.schedule_tasks:
            try:
                parts = task_config.split(' ', 1)
                if len(parts) != 2:
                    logger.error(f"无效的定时任务配置: {task_config}")
                    continue
                    
                schedule_time, cmd = parts
                
                # 支持多种定时格式
                if ':' in schedule_time:
                    # 每天特定时间
                    schedule.every().day.at(schedule_time).do(self.execute_command, cmd)
                    logger.info(f"添加定时任务: 每天 {schedule_time} 执行 '{cmd}'")
                elif schedule_time.endswith('s'):
                    # 每秒执行
                    seconds = int(schedule_time[:-1])
                    schedule.every(seconds).seconds.do(self.execute_command, cmd)
                    logger.info(f"添加定时任务: 每 {seconds} 秒执行 '{cmd}'")
                elif schedule_time.endswith('m'):
                    # 每分钟执行
                    minutes = int(schedule_time[:-1])
                    schedule.every(minutes).minutes.do(self.execute_command, cmd)
                    logger.info(f"添加定时任务: 每 {minutes} 分钟执行 '{cmd}'")
                elif schedule_time.endswith('h'):
                    # 每小时执行
                    hours = int(schedule_time[:-1])
                    schedule.every(hours).hours.do(self.execute_command, cmd)
                    logger.info(f"添加定时任务: 每 {hours} 小时执行 '{cmd}'")
                else:
                    logger.error(f"不支持的定时格式: {schedule_time}")
            except Exception as e:
                logger.error(f"设置定时任务失败: {task_config}, 错误: {e}")
    
    def pause(self):
        """暂停执行"""
        with self.lock:
            if self.is_running and not self.is_paused:
                self.is_paused = True
                logger.info("自动执行器已暂停")
                return True
        return False
    
    def resume(self):
        """恢复执行"""
        with self.lock:
            if self.is_running and self.is_paused:
                self.is_paused = False
                logger.info("自动执行器已恢复")
                return True
        return False
    
    def stop(self):
        """停止执行"""
        with self.lock:
            if self.is_running:
                self.is_running = False
                self.is_paused = False
                logger.info("正在停止自动执行器...")
            else:
                return False
        
        # 等待线程结束
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # 清理线程池
        self.executor.shutdown(wait=False)
        
        logger.info("自动执行器已停止")
        return True
    
    def add_command(self, cmd, group="default"):
        """添加命令"""
        with self.lock:
            # 确保分组存在
            if group not in self.command_groups:
                self.command_groups[group] = []
            
            # 添加命令
            if cmd not in self.command_groups[group]:
                self.command_groups[group].append(cmd)
                logger.info(f"在分组 {group} 添加命令: {cmd}")
                return True
        return False
    
    def remove_command(self, cmd, group="default"):
        """移除命令"""
        with self.lock:
            if group in self.command_groups and cmd in self.command_groups[group]:
                self.command_groups[group].remove(cmd)
                # 如果分组为空，删除分组
                if not self.command_groups[group]:
                    del self.command_groups[group]
                    # 如果删除的是激活组，从激活组中移除
                    if group in self.active_groups:
                        self.active_groups.remove(group)
                logger.info(f"从分组 {group} 移除命令: {cmd}")
                return True
        return False
    
    def create_group(self, group_name):
        """创建命令组"""
        with self.lock:
            if group_name not in self.command_groups:
                self.command_groups[group_name] = []
                logger.info(f"创建命令组: {group_name}")
                return True
        return False
    
    def delete_group(self, group_name):
        """删除命令组"""
        with self.lock:
            if group_name != "default" and group_name in self.command_groups:
                del self.command_groups[group_name]
                # 从激活组中移除
                if group_name in self.active_groups:
                    self.active_groups.remove(group_name)
                logger.info(f"删除命令组: {group_name}")
                return True
        return False
    
    def activate_group(self, group_name):
        """激活命令组"""
        with self.lock:
            if group_name in self.command_groups and group_name not in self.active_groups:
                self.active_groups.append(group_name)
                logger.info(f"激活命令组: {group_name}")
                return True
        return False
    
    def deactivate_group(self, group_name):
        """停用命令组"""
        with self.lock:
            if group_name != "default" and group_name in self.active_groups:
                self.active_groups.remove(group_name)
                logger.info(f"停用命令组: {group_name}")
                return True
        return False
    
    def set_interval(self, seconds):
        """设置执行间隔"""
        try:
            seconds = int(seconds)
            if seconds < 1:
                logger.warning("执行间隔过小，已设置为1秒")
                seconds = 1
            
            with self.lock:
                self.interval = seconds
            logger.info(f"设置执行间隔: {self.interval}秒")
            return True
        except ValueError:
            logger.error(f"无效的间隔值: {seconds}")
            return False
    
    def export_history(self, filename="execution_history.json"):
        """导出执行历史到JSON文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.execution_history, f, ensure_ascii=False, indent=2)
            logger.info(f"执行历史已导出到 {filename}")
            return True
        except Exception as e:
            logger.error(f"导出执行历史失败: {e}")
            return False
    
    def get_status(self):
        """获取当前状态"""
        with self.lock:
            status = {
                "running": self.is_running,
                "paused": self.is_paused,
                "interval": self.interval,
                "execution_count": self.execution_count,
                "last_execution": self.last_execution.isoformat() if self.last_execution else None,
                "command_groups": {k: len(v) for k, v in self.command_groups.items()},
                "active_groups": self.active_groups,
                "schedule_tasks": len(self.schedule_tasks),
                "monitoring_rules": len(self.monitoring_rules),
                "history_count": len(self.execution_history)
            }
        return status

def _safe_print(text):
    """安全打印函数，处理各种编码问题"""
    try:
        # 确保是字符串类型
        if not isinstance(text, str):
            text = str(text)
        
        # Windows环境下的特殊处理
        if sys.platform.startswith('win'):
            # 尝试使用不同的编码输出
            try:
                print(text)
            except UnicodeEncodeError:
                # 替换无法打印的字符
                safe_text = ''.join(c if ord(c) < 128 or (0x4e00 <= ord(c) <= 0x9fff) else '?' for c in text)
                print(safe_text)
        else:
            print(text)
    except Exception as e:
        # 最极端情况下的保障
        try:
            print(f"[输出错误] {str(e)}")
        except:
            pass

def show_help():
    """显示帮助信息"""
    _safe_print("\n===========================================")
    _safe_print("AWD高级自动化命令执行器 V2.0 - 帮助信息")
    _safe_print("===========================================")
    
    _safe_print("\n基础命令:")
    _safe_print("  start          - 开始自动执行命令")
    _safe_print("  pause          - 暂停执行")
    _safe_print("  resume         - 恢复执行")
    _safe_print("  stop           - 停止执行")
    _safe_print("  status         - 查看当前状态")
    _safe_print("  help           - 显示此帮助信息")
    _safe_print("  clear          - 清除控制台输出")
    _safe_print("  exit/quit/q    - 退出程序")
    
    _safe_print("\n命令管理:")
    _safe_print("  add <命令> [分组]       - 添加命令到指定分组(默认default)")
    _safe_print("  remove <命令> [分组]    - 从指定分组移除命令")
    _safe_print("  list [分组]             - 列出指定分组的所有命令")
    _safe_print("  interval <秒数>         - 设置执行间隔")
    
    _safe_print("\n分组管理:")
    _safe_print("  group create <名称>     - 创建新命令组")
    _safe_print("  group delete <名称>     - 删除命令组(除default外)")
    _safe_print("  group activate <名称>   - 激活命令组")
    _safe_print("  group deactivate <名称> - 停用命令组")
    _safe_print("  group list              - 列出所有命令组")
    
    _safe_print("\n高级功能:")
    _safe_print("  schedule <时间> <命令>  - 添加定时任务(格式: 10s/5m/3h 或 14:30)")
    _safe_print("  monitor add <规则> <值> - 添加监控规则")
    _safe_print("  monitor list            - 列出监控规则")
    _safe_print("  export [文件名]         - 导出执行历史")
    _safe_print("  save                    - 保存配置")
    _safe_print("  load                    - 重新加载配置")
    
    _safe_print("\n定时任务格式示例:")
    _safe_print("  10s    - 每10秒执行一次")
    _safe_print("  5m     - 每5分钟执行一次")
    _safe_print("  2h     - 每2小时执行一次")
    _safe_print("  14:30  - 每天14:30执行")
    
    _safe_print("\n监控规则示例:")
    _safe_print("  monitor add contains error,失败,警告")
    _safe_print("  monitor add max_time 30")
    _safe_print("  monitor add returncode 0,1,2")
    
    _safe_print("\n使用示例:")
    _safe_print("  add dir /b monitor       - 将dir /b命令添加到monitor分组")
    _safe_print("  group create security    - 创建名为security的命令组")
    _safe_print("  interval 120             - 设置执行间隔为120秒")
    _safe_print("  schedule 30s echo hello  - 添加每30秒执行一次的定时任务")
    
def main():
    """主函数"""
    executor = CommandExecutor()
    executor.load_config()
    
    _safe_print("===== AWD高级自动化命令执行器 V2.0 =====")
    _safe_print(f"配置的命令组: {list(executor.command_groups.keys())}")
    _safe_print(f"激活的组: {executor.active_groups}")
    _safe_print(f"执行间隔: {executor.interval}秒")
    _safe_print(f"定时任务数: {len(executor.schedule_tasks)}")
    _safe_print(f"监控规则数: {len(executor.monitoring_rules)}")
    _safe_print("  start          - 开始自动执行")
    _safe_print("  pause          - 暂停执行")
    _safe_print("  resume         - 恢复执行")
    _safe_print("  stop           - 停止执行")
    _safe_print("  status         - 查看当前状态")
    _safe_print("  exit/quit/q    - 退出程序")
    
    _safe_print("\n命令管理:")
    _safe_print("  add <命令> [分组]       - 添加命令到指定分组(默认default)")
    _safe_print("  remove <命令> [分组]    - 从指定分组移除命令")
    _safe_print("  list [分组]             - 列出指定分组的所有命令")
    _safe_print("  interval <秒数>         - 设置执行间隔")
    
    _safe_print("\n分组管理:")
    _safe_print("  group create <名称>     - 创建新命令组")
    _safe_print("  group delete <名称>     - 删除命令组(除default外)")
    _safe_print("  group activate <名称>   - 激活命令组")
    _safe_print("  group deactivate <名称> - 停用命令组")
    _safe_print("  group list              - 列出所有命令组")
    
    _safe_print("\n高级功能:")
    _safe_print("  schedule <时间> <命令>  - 添加定时任务(格式: 10s/5m/3h 或 14:30)")
    _safe_print("  monitor add <规则> <值> - 添加监控规则")
    _safe_print("  monitor list            - 列出监控规则")
    _safe_print("  export [文件名]         - 导出执行历史")
    _safe_print("  save                    - 保存配置")
    _safe_print("  load                    - 重新加载配置")
    _safe_print("===============================\n")
    
    try:
        while True:
            cmd_input = input("请输入命令: ").strip().lower()
            parts = cmd_input.split()
            
            if not parts:
                continue
                
            cmd = parts[0]
            
            if cmd == 'start':
                executor.start()
            elif cmd == 'pause':
                executor.pause()
            elif cmd == 'resume':
                executor.resume()
            elif cmd == 'stop':
                executor.stop()
            elif cmd == 'status':
                status = executor.get_status()
                _safe_print("\n当前状态:")
                _safe_print(f"  运行状态: {'运行中' if status['running'] else '已停止'}{'(已暂停)' if status['paused'] else ''}")
                _safe_print(f"  执行间隔: {status['interval']}秒")
                _safe_print(f"  已执行轮数: {status['execution_count']}")
                _safe_print(f"  最后执行时间: {status['last_execution'] or '从未执行'}")
                _safe_print(f"  命令组数: {len(status['command_groups'])}")
                _safe_print(f"  激活组数: {len(status['active_groups'])}")
                _safe_print(f"  定时任务: {status['schedule_tasks']}")
                _safe_print(f"  监控规则: {status['monitoring_rules']}")
                _safe_print(f"  历史记录: {status['history_count']}")
                _safe_print("\n命令组详情:")
                for group_name, cmd_count in status['command_groups'].items():
                    active = "(激活)" if group_name in status['active_groups'] else "(停用)"
                    _safe_print(f"    {group_name}: {cmd_count} 条命令 {active}")
                _safe_print()
            elif cmd == 'help':
                show_help()
            elif cmd == 'clear':
                # 清除控制台
                os.system('cls' if os.name == 'nt' else 'clear')
                # 重新显示程序信息
                _safe_print("===== AWD高级自动化命令执行器 V2.0 =====")
                _safe_print(f"配置的命令组: {list(executor.command_groups.keys())}")
                _safe_print(f"激活的组: {executor.active_groups}")
                _safe_print(f"执行间隔: {executor.interval}秒")
                _safe_print(f"定时任务数: {len(executor.schedule_tasks)}")
                _safe_print(f"监控规则数: {len(executor.monitoring_rules)}")
                _safe_print("===============================")
            elif cmd in ('exit', 'quit', 'q'):
                executor.stop()
                _safe_print("程序已退出")
                break
            elif cmd == 'add' and len(parts) >= 2:
                if len(parts) >= 3:
                    executor.add_command(' '.join(parts[1:-1]), parts[-1])
                else:
                    executor.add_command(' '.join(parts[1:]))
            elif cmd == 'remove' and len(parts) >= 2:
                if len(parts) >= 3:
                    executor.remove_command(' '.join(parts[1:-1]), parts[-1])
                else:
                    executor.remove_command(' '.join(parts[1:]))
            elif cmd == 'list':
                group = parts[1] if len(parts) > 1 else None
                if group:
                    if group in executor.command_groups:
                        _safe_print(f"\n{group} 命令组:")
                        for i, command in enumerate(executor.command_groups[group], 1):
                            _safe_print(f"  {i}. {command}")
                    else:
                        _safe_print(f"命令组 '{group}' 不存在")
                else:
                    _safe_print("\n所有命令组:")
                    for group_name, commands in executor.command_groups.items():
                        active = "(激活)" if group_name in executor.active_groups else "(停用)"
                        _safe_print(f"\n{group_name} {active}:")
                        for i, command in enumerate(commands, 1):
                            _safe_print(f"  {i}. {command}")
                _safe_print()
            elif cmd == 'interval' and len(parts) > 1:
                executor.set_interval(parts[1])
                
            # 分组管理
            elif cmd == 'group' and len(parts) >= 2:
                action = parts[1]
                if action == 'create' and len(parts) > 2:
                    executor.create_group(parts[2])
                elif action == 'delete' and len(parts) > 2:
                    executor.delete_group(parts[2])
                elif action == 'activate' and len(parts) > 2:
                    executor.activate_group(parts[2])
                elif action == 'deactivate' and len(parts) > 2:
                    executor.deactivate_group(parts[2])
                elif action == 'list':
                    _safe_print("\n命令组列表:")
                    for group_name, commands in executor.command_groups.items():
                        active = "(激活)" if group_name in executor.active_groups else "(停用)"
                        _safe_print(f"  {group_name}: {len(commands)} 条命令 {active}")
                    _safe_print("")  # 空行，提供空字符串参数
                else:
                    _safe_print("无效的分组操作")
                    
            # 高级功能
            elif cmd == 'schedule' and len(parts) >= 3:
                schedule_time = parts[1]
                command_to_schedule = ' '.join(parts[2:])
                executor.schedule_tasks.append(f"{schedule_time} {command_to_schedule}")
                logger.info(f"添加定时任务: {schedule_time} {command_to_schedule}")
                # 如果正在运行，重新设置定时任务
                if executor.is_running:
                    executor._setup_scheduled_tasks()
            elif cmd == 'monitor' and len(parts) >= 2:
                action = parts[1]
                if action == 'add' and len(parts) >= 4:
                    rule_name = parts[2]
                    rule_value = ' '.join(parts[3:])
                    executor.monitoring_rules[rule_name] = rule_value
                    logger.info(f"添加监控规则: {rule_name}={rule_value}")
                elif action == 'list':
                    _safe_print("\n监控规则列表:")
                    if executor.monitoring_rules:
                        for rule_name, rule_value in executor.monitoring_rules.items():
                            _safe_print(f"  {rule_name}: {rule_value}")
                    else:
                        _safe_print("  暂无监控规则")
                    _safe_print()
                else:
                    _safe_print("无效的监控操作")
            elif cmd == 'export':
                filename = parts[1] if len(parts) > 1 else "execution_history.json"
                executor.export_history(filename)
            elif cmd == 'save':
                executor.save_config()
            elif cmd == 'load':
                executor.load_config()
            else:
                _safe_print("未知命令，请重新输入")
                
    except KeyboardInterrupt:
        _safe_print("\n检测到Ctrl+C，正在退出...")
        executor.stop()
    except Exception as e:
        _safe_print(f"程序发生异常: {str(e)}")
        logger.error(f"程序异常: {str(e)}", exc_info=True)
        executor.stop()

if __name__ == "__main__":
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    main()