#!/usr/bin/env python3

import subprocess
import time
import pexpect
import re
from datetime import datetime
import sys
import logging

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('/share/power_cycle_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # 循环执行10次
    for cycle in range(1, 21):
        logger.info("=== 开始第 %d 次循环 ===", cycle)
        
        # 1. 执行电源下电操作
        logger.info("执行电源下电操作...")
        for node in [3, 6, 9, 12]:
            # 先检查节点当前状态
            status_cmd = f"mgmt_tool node power get -n {node}"
            try:
                status_result = subprocess.run(status_cmd, shell=True, check=False, capture_output=True, text=True)
                if status_result.returncode == 0:
                    logger.info("节点 %d 当前状态: %s", node, status_result.stdout.strip())
                    if "power off" in status_result.stdout:
                        logger.info("节点 %d 已处于下电状态，跳过下电操作", node)
                        continue
                else:
                    logger.warning("获取节点 %d 状态失败: %s", node, status_result.stderr.strip())
            except Exception as e:
                logger.error("获取节点 %d 状态时发生异常: %s", node, e)
            
            # 尝试下电
            off_cmd = f"mgmt_tool node power off -n {node}"
            logger.info("执行命令: %s", off_cmd)
            
            # 添加重试机制
            retry_count = 0
            max_retries = 3
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    result = subprocess.run(off_cmd, shell=True, check=False, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("SUCCEED: %s", result.stdout.strip())
                        success = True
                    else:
                        logger.warning("FAILED: 命令返回状态码 %d", result.returncode)
                        logger.warning("错误输出: %s", result.stderr.strip())
                        retry_count += 1
                        
                        if retry_count < max_retries:
                            # 尝试先重置节点，再下电
                            if retry_count == 2:
                                logger.info("尝试下电节点 %d 后再下电...", node)
                                reset_cmd = f"mgmt_tool node power off -n {node}"
                                reset_result = subprocess.run(reset_cmd, shell=True, check=False, capture_output=True, text=True)
                                logger.info("下电命令结果: %s", reset_result.stdout.strip())
                                time.sleep(5)
                            
                            logger.info("等待3秒后重试 (%d/%d)...", retry_count, max_retries)
                            time.sleep(3)
                except Exception as e:
                    logger.error("执行命令时发生异常: %s", e)
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info("等待3秒后重试 (%d/%d)...", retry_count, max_retries)
                        time.sleep(3)
            
            if not success:
                logger.warning("警告: 节点 %d 下电失败，尝试继续下一个节点...", node)
                # 不抛出异常，继续处理其他节点
                continue
        
        # 等待2秒确保下电完成
        time.sleep(2)
        
        # 2. 执行电源上电操作
        logger.info("执行电源上电操作...")
        for node in [3, 6, 9, 12]:
            # 先检查节点当前状态
            status_cmd = f"mgmt_tool node power get -n {node}"
            try:
                status_result = subprocess.run(status_cmd, shell=True, check=False, capture_output=True, text=True)
                if status_result.returncode == 0:
                    logger.info("节点 %d 当前状态: %s", node, status_result.stdout.strip())
                    if "power on" in status_result.stdout:
                        logger.info("节点 %d 已处于上电状态，跳过上电操作", node)
                        continue
                else:
                    logger.warning("获取节点 %d 状态失败: %s", node, status_result.stderr.strip())
            except Exception as e:
                logger.error("获取节点 %d 状态时发生异常: %s", node, e)
            
            # 尝试上电
            on_cmd = f"mgmt_tool node power on -n {node}"
            logger.info("执行命令: %s", on_cmd)
            
            # 添加重试机制
            retry_count = 0
            max_retries = 3
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    result = subprocess.run(on_cmd, shell=True, check=False, capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("SUCCEED: %s", result.stdout.strip())
                        success = True
                    else:
                        logger.warning("FAILED: 命令返回状态码 %d", result.returncode)
                        logger.warning("错误输出: %s", result.stderr.strip())
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.info("等待3秒后重试 (%d/%d)...", retry_count, max_retries)
                            time.sleep(3)
                except Exception as e:
                    logger.error("执行命令时发生异常: %s", e)
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info("等待3秒后重试 (%d/%d)...", retry_count, max_retries)
                        time.sleep(3)
            
            if not success:
                logger.warning("警告: 节点 %d 上电失败，尝试继续下一个节点...", node)
                # 不抛出异常，继续处理其他节点
                continue
        
        # 等待40秒确保系统完全启动
        wait_time = 35
        logger.info("等待%d秒让系统完全启动...", wait_time)
        
        # 优化的进度条实现 - 同一行更新，避免产生多行输出
        try:
            for i in range(wait_time):
                # 计算进度百分比
                progress = (i + 1) / wait_time
                percent = int(progress * 100)
                
                # 创建图形化进度条（20个字符宽度）
                bar_width = 60
                filled_length = int(bar_width * progress)
                bar = '=' * filled_length + '-' * (bar_width - filled_length)
                
                # 使用回车符清除当前行并显示进度条，不换行
                print(f"\r[{bar}] {percent}% ({i + 1}/{wait_time}秒)", end="", flush=True)
                
                # 仅在最后记录一次完整的日志，避免干扰进度条显示
                if (i + 1) == wait_time:
                    print()
                    logger.info("已等待 %d 秒完成", i + 1)
                
                time.sleep(1)
        except KeyboardInterrupt:
            print()  # 先换行，确保错误信息显示在新行
            logger.info("用户中断了等待过程")
            raise
        
        # 完成后换行
        print()
        logger.info("系统启动等待完成")
        
        # 3. 通过指令进入串口终端并执行命令
        logger.info("进入串口终端并执行命令...")
        
        # 打开串口终端
        child = pexpect.spawn("picocom -b 115200 /dev/ttyS6")
        
        try:
            # 等待终端初始化，然后发送回车以获取提示符
            time.sleep(2)  # 等待2秒让终端初始化
            
            # 发送回车
            child.sendline("")
            
            # 等待终端提示符出现
            child.expect("Console#", timeout=60)
            logger.info("成功进入串口终端")
            
            # 执行show interfaces status all命令
            child.sendline("show interfaces status all")
            
            # 收集输出，处理分页
            output = ""
            while True:
                try:
                    index = child.expect(["Type <CR> to continue, Q<CR> to stop:", "Console#"], timeout=30)
                    if index == 0:
                        # 处理分页提示，按回车继续
                        output += child.before.decode()
                        child.sendline("")
                    else:
                        # 命令执行完成，获取剩余输出
                        output += child.before.decode()
                        break
                except pexpect.TIMEOUT:
                    logger.warning("命令执行超时")
                    break
            
            logger.info("成功获取命令输出")
            
            # 4. 解析数据
            logger.info("解析端口状态数据...")
            
            # 解析Dev/Port和Link状态
            interfaces = []
            # 使用正则表达式匹配端口信息行
            pattern = r'^(\d+/\d+)\s+\S+\s+(Up|Down)\s+'
            lines = output.split('\n')
            
            for line in lines:
                match = re.match(pattern, line.strip())
                if match:
                    port = match.group(1)
                    link = match.group(2)
                    interfaces.append((port, link))
            
            logger.info("成功解析 %d 个端口状态", len(interfaces))
            
            # 5. 保存到test.log文件
            logger.info("保存数据到test.log文件...")
            with open("/share/test.log", "a") as f:
                # 写入循环次数和执行时间
                f.write(f"循环次数: {cycle}\n")
                f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # 写入端口状态（横向排布，按数字顺序）
                # 自定义排序函数：按端口号数字排序
                def sort_key(interface):
                    port, link = interface
                    dev, port_num = map(int, port.split('/'))
                    return (dev, port_num)
                
                sorted_interfaces = sorted(interfaces, key=sort_key)
                
                # 使用固定宽度格式化，使Dev/Port和Link列对齐
                # 动态计算端口号的最大宽度
                max_port_width = max(len(port) for port, link in sorted_interfaces)
                # 状态宽度固定为3（Up和Down都是3个字符）
                status_width = 3
                
                # 构建格式化的端口和状态字符串
                formatted_ports = []
                formatted_links = []
                for port, link in sorted_interfaces:
                    # 端口号使用固定宽度左对齐
                    formatted_port = f"{port:<{max_port_width}}"
                    # 状态使用固定宽度左对齐
                    formatted_link = f"{link:<{status_width}}"
                    formatted_ports.append(formatted_port)
                    formatted_links.append(formatted_link)
                
                # 合并为字符串，项目之间用空格分隔
                ports_str = " ".join(formatted_ports)
                links_str = " ".join(formatted_links)
                
                f.write(f"Dev/Port: {ports_str}\n")
                f.write(f"Link:     {links_str}\n")
                
                f.write("\n")
            
            logger.info("数据保存完成")
            
        except pexpect.EOF:
            logger.warning("串口终端意外关闭")
        except pexpect.TIMEOUT:
            logger.warning("进入串口终端超时")
        except Exception as e:
            logger.error("串口操作过程中发生错误: %s", e)
        finally:
            # 5. 退出串口终端（Ctrl+A+Q）
            logger.info("退出串口终端...")
            try:
                # 检查child对象是否存在且有效
                if 'child' in locals() and child is not None:
                    # 首先尝试标准退出序列
                    try:
                        # 尝试多种退出序列
                        logger.info("尝试退出序列: Ctrl+A+Q...")
                        child.send('\x01q')  # 发送 Ctrl+A+Q 组合序列
                        time.sleep(0.5)
                        
                        if child.isalive():
                            logger.info("尝试退出序列: Ctrl+A+X...")
                            child.send('\x01x')  # 发送 Ctrl+A+X 组合序列
                            time.sleep(0.5)
                    except Exception as send_e:
                        logger.warning("发送退出序列失败: %s", send_e)
                    
                    # 检查进程是否仍在运行
                    if child.isalive():
                        logger.warning("串口终端仍在运行，正在终止...")
                        try:
                            # 先尝试优雅终止
                            child.terminate()
                            time.sleep(1)
                            
                            # 检查是否终止成功
                            if child.isalive():
                                logger.warning("优雅终止失败，尝试强制终止...")
                                child.kill()
                                time.sleep(0.5)
                        except Exception as terminate_e:
                            logger.error("终止串口终端时发生错误: %s", terminate_e)
                        
                        # 最终检查
                        if child.isalive():
                            logger.warning("警告: 无法通过编程方式终止picocom，可能需要手动干预！")
                        else:
                            logger.info("串口终端已成功终止")
                    else:
                        logger.info("串口终端已正常退出")
                        
                    # 最后再次检查
                    if not child.isalive():
                        logger.info("串口终端已终止")
                    else:
                        logger.warning("警告：无法终止串口终端进程")
                else:
                    logger.info("没有检测到有效的串口终端对象")
                    
            except KeyboardInterrupt:
                logger.info("检测到用户中断，正在清理资源...")
                if 'child' in locals() and child is not None:
                    try:
                        child.kill()
                        logger.info("强制终止串口终端")
                    except:
                        pass
            except Exception as finally_e:
                logger.error("退出串口终端时发生错误: %s", finally_e)
        
        logger.info("=== 第 %d 次循环完成 ===", cycle)

if __name__ == "__main__":
    main()