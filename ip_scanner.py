import ipaddress
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

# 定义颜色常量
class Colors:
    if sys.platform.startswith('win'):
        # Windows系统颜色代码
        try:
            import ctypes
            # 获取Windows控制台句柄
            STD_OUTPUT_HANDLE = -11
            hConsole = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            
            # 定义颜色常量
            RESET = ''
            GREEN = ''
            RED = ''
            YELLOW = ''
            BLUE = ''
            CYAN = ''
            
            @classmethod
            def set_color(cls, color_code):
                ctypes.windll.kernel32.SetConsoleTextAttribute(cls.hConsole, color_code)
            
            # 颜色打印装饰器
            @staticmethod
            def print_color(text, color_code):
                try:
                    import ctypes
                    STD_OUTPUT_HANDLE = -11
                    hConsole = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
                    ctypes.windll.kernel32.SetConsoleTextAttribute(hConsole, color_code)
                    print(text)
                    ctypes.windll.kernel32.SetConsoleTextAttribute(hConsole, 7)  # 重置为默认颜色
                except:
                    # 如果无法设置颜色，使用无颜色输出
                    print(text)
        except:
            # 如果无法设置颜色，使用无颜色输出
            RESET = ''
            GREEN = ''
            RED = ''
            YELLOW = ''
            BLUE = ''
            CYAN = ''
            
            @staticmethod
            def print_color(text, color_code):
                print(text)
    else:
        # Linux/macOS系统ANSI颜色代码
        RESET = '\033[0m'
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        
        @staticmethod
        def print_color(text, color_code):
            color_map = {
                10: '\033[92m',  # 绿色
                12: '\033[91m',  # 红色
                14: '\033[93m',  # 黄色
                9:  '\033[94m',  # 蓝色
                11: '\033[96m',  # 青色
            }
            color = color_map.get(color_code, '')
            print(f"{color}{text}{'\033[0m'}")

# ping测试函数
def ping_ip(ip, count=1, timeout=500):
    """测试单个IP是否可达
    
    Args:
        ip: IP地址对象
        count: ping包数量
        timeout: 超时时间（毫秒）
    
    Returns:
        bool: IP是否可达
    """
    try:
        # 根据操作系统选择ping命令和参数
        ip_str = str(ip)
        if sys.platform.startswith('win'):
            # Windows系统ping命令 - 减少ping次数提高速度
            command = ['ping', '-n', str(count), '-w', str(timeout), ip_str]
        else:
            # Linux/macOS系统ping命令 - 减少ping次数提高速度
            command = ['ping', '-c', str(count), '-W', str(timeout//1000), ip_str]
        
        # 执行ping命令，捕获输出
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            timeout=timeout/1000 + 1  # 防止命令执行超时
        )
        
        stdout = result.stdout
        
        # 分析输出内容
        has_reply = "来自" in stdout or "Reply from" in stdout or "64 bytes from" in stdout
        has_ttl = "TTL=" in stdout or "ttl=" in stdout
        has_unreachable = "无法访问目标主机" in stdout or "Destination host unreachable" in stdout or "unreachable" in stdout.lower()
        
        # 综合判断是否可达：
        # 1. 必须有TTL值（表示成功收到回复）
        # 2. 不能包含"无法访问目标主机"或"unreachable"
        # 3. 考虑返回码，但优先级低于实际输出内容
        is_reachable = (has_ttl and not has_unreachable) or \
                      (result.returncode == 0 and has_reply and not has_unreachable)
        
        return is_reachable
    except subprocess.TimeoutExpired:
        # 命令执行超时
        return False
    except Exception as e:
        # 其他异常
        return False

# 扫描IP函数
def scan_ip(ip, reachable_list, unreachable_list, lock, progress_callback=None, count=1, timeout=500):
    """扫描单个IP并更新结果列表
    
    Args:
        ip: IP地址对象
        reachable_list: 存储可达IP的列表
        unreachable_list: 存储不可达IP的列表
        lock: 线程锁
        progress_callback: 进度回调函数
        count: ping包数量
        timeout: 超时时间（毫秒）
    """
    is_reachable = ping_ip(ip, count=count, timeout=timeout)
    with lock:
        if is_reachable:
            reachable_list.append(str(ip))
            if sys.platform.startswith('win'):
                Colors.print_color(f"[可达] {ip}", 10)  # 10: 绿色背景黑色文字
            else:
                print(f"[{Colors.GREEN}可达{Colors.RESET}] {ip}")
        else:
            unreachable_list.append(str(ip))
            if sys.platform.startswith('win'):
                Colors.print_color(f"[不可达] {ip}", 12)  # 12: 红色背景黑色文字
            else:
                print(f"[{Colors.RED}不可达{Colors.RESET}] {ip}")
        
        # 调用进度回调函数
        if progress_callback:
            progress_callback()

# 解析网段
def parse_network(network):
    """解析网段，返回IP地址列表"""
    try:
        ip_net = ipaddress.ip_network(network, strict=False)
        return list(ip_net.hosts())
    except ValueError as e:
        print(f"[错误] 网段格式错误: {e}")
        return []

# 显示结果表格
def show_results_table(reachable, unreachable):
    """以表格形式显示扫描结果"""
    # 计算统计数据
    total = len(reachable) + len(unreachable)
    reachable_count = len(reachable)
    unreachable_count = len(unreachable)
    
    if total == 0:
        print("\n[错误] 没有可显示的结果")
        return
    
    # 显示统计信息表格
    if sys.platform.startswith('win'):
        print("\n" + "╚══════════════════════════════════════════════════════╝")
        Colors.print_color("╔══════════════════════════════════════════════════════╗", 11)  # 11: 青色背景黑色文字
        Colors.print_color("║                  扫描结果统计                      ║", 11)
        Colors.print_color("╠══════════════════════════════════════════════════════╣", 11)
    else:
        print(f"\n{Colors.CYAN}╚══════════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"{Colors.CYAN}╔══════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║                  扫描结果统计                      ║{Colors.RESET}")
        print(f"{Colors.CYAN}╠══════════════════════════════════════════════════════╣{Colors.RESET}")
    
    print(f"| {'统计项':<15} | {'数值':<10} | {'比例':<15} |")
    print(f"|{'-'*17}|{'-'*12}|{'-'*17}|")
    print(f"| {'总IP数':<15} | {total:<10} | {'100%':<15} |")
    print(f"| {'可达IP数':<15} | {reachable_count:<10} | {reachable_count/total*100:>7.1f}%{'':<7} |")
    print(f"| {'不可达IP数':<15} | {unreachable_count:<10} | {unreachable_count/total*100:>7.1f}%{'':<7} |")
    
    if sys.platform.startswith('win'):
        Colors.print_color("╚══════════════════════════════════════════════════════╝", 11)
    else:
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════════╝{Colors.RESET}")
    
    # 显示可达IP表格
    if sys.platform.startswith('win'):
        Colors.print_color(f"\n可达IP列表 ({len(reachable)}个):", 10)
    else:
        print(f"\n{Colors.GREEN}可达IP列表 ({len(reachable)}个):{Colors.RESET}")
    if sys.platform.startswith('win'):
        Colors.print_color("╟──────────────────────────────────────────────────────╢", 10)
    else:
        print(f"{Colors.GREEN}╟──────────────────────────────────────────────────────╢{Colors.RESET}")
    if reachable:
        # 根据终端宽度动态调整每行显示的IP数量
        try:
            terminal_width = os.get_terminal_size().columns
            ip_per_row = max(3, min(10, terminal_width // 17))  # 每个IP占16字符+1空格
        except:
            ip_per_row = 5  # 默认为5个IP/行
            
        rows = (len(reachable) + ip_per_row - 1) // ip_per_row
        
        # 对IP列表进行排序
        sorted_reachable = sorted(reachable, key=lambda x: tuple(map(int, x.split('.'))))
        
        for i in range(rows):
            start = i * ip_per_row
            end = min((i + 1) * ip_per_row, len(sorted_reachable))
            row_ips = sorted_reachable[start:end]
            # 格式化输出IP，每个IP占16字符宽度
            formatted_ips = [f"{ip:<16}" for ip in row_ips]
            print("   " + "".join(formatted_ips))
    else:
        print("   无可达IP")
    if sys.platform.startswith('win'):
        Colors.print_color("╚──────────────────────────────────────────────────────╝", 10)
    else:
        print(f"{Colors.GREEN}╚──────────────────────────────────────────────────────╝{Colors.RESET}")
    
    # 显示不可达IP表格
    if sys.platform.startswith('win'):
        Colors.print_color(f"\n不可达IP列表 ({len(unreachable)}个):", 12)
        Colors.print_color("╟──────────────────────────────────────────────────────╢", 12)
    else:
        print(f"\n{Colors.RED}不可达IP列表 ({len(unreachable)}个):{Colors.RESET}")
        print(f"{Colors.RED}╟──────────────────────────────────────────────────────╢{Colors.RESET}")
    if unreachable:
        # 根据终端宽度动态调整每行显示的IP数量
        try:
            terminal_width = os.get_terminal_size().columns
            ip_per_row = max(3, min(10, terminal_width // 17))  # 每个IP占16字符+1空格
        except:
            ip_per_row = 5  # 默认为5个IP/行
            
        rows = (len(unreachable) + ip_per_row - 1) // ip_per_row
        
        # 对IP列表进行排序
        sorted_unreachable = sorted(unreachable, key=lambda x: tuple(map(int, x.split('.'))))
        
        for i in range(rows):
            start = i * ip_per_row
            end = min((i + 1) * ip_per_row, len(sorted_unreachable))
            row_ips = sorted_unreachable[start:end]
            # 格式化输出IP，每个IP占16字符宽度
            formatted_ips = [f"{ip:<16}" for ip in row_ips]
            print("   " + "".join(formatted_ips))
    else:
        print("   无不可达IP")
    if sys.platform.startswith('win'):
        Colors.print_color("╚──────────────────────────────────────────────────────╝", 12)
    else:
        print(f"{Colors.RED}╚──────────────────────────────────────────────────────╝{Colors.RESET}")

# 绘制IP可达性图形
def plot_ip_status(network, reachable, unreachable):
    """绘制IP可达性状态图形，绿色表示可达，红色表示不可达"""
    try:
        # 配置matplotlib使用支持中文的字体，解决中文显示异常问题
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        
        # 解析网段
        ip_net = ipaddress.ip_network(network, strict=False)
        all_ips = list(ip_net.hosts())
        
        if not all_ips:
            print("[错误] 网段中没有可用的主机IP")
            return
        
        # 转换为字符串列表以便比较
        all_ips_str = [str(ip) for ip in all_ips]
        reachable_set = set(reachable)
        
        # 计算网格大小
        total_ips = len(all_ips_str)
        grid_cols = min(20, total_ips)  # 每行最多20个IP
        grid_rows = (total_ips + grid_cols - 1) // grid_cols
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 设置图形标题
        plt.title(f"IP地址可达性状态 - {network}", fontsize=16, pad=20)
        
        # 计算每个方块的大小和间距
        box_size = 0.8
        spacing = 0.2  # 增加间距，提高可读性
        
        # 绘制IP地址方块
        for idx, ip in enumerate(all_ips_str):
            row = idx // grid_cols
            col = idx % grid_cols
            
            # 计算位置
            x = col * (box_size + spacing)
            y = -row * (box_size + spacing)
            
            # 确定颜色：绿色表示可达，红色表示不可达
            if ip in reachable_set:
                color = '#2ECC71'  # 亮绿色，更明显
                status = '可达'
            else:
                color = '#E74C3C'  # 亮红色，更明显
                status = '不可达'
            
            # 绘制方块
            rect = patches.Rectangle(
                (x, y), box_size, box_size, 
                linewidth=1, edgecolor='black', facecolor=color
            )
            ax.add_patch(rect)
            
            # 在方块内添加IP地址（只显示最后一位）
            ip_last = ip.split('.')[-1]
            plt.text(
                x + box_size/2, y + box_size/2, 
                ip_last, ha='center', va='center', 
                fontsize=9, color='white'  # 所有彩色方块上都使用白色文字
            )
        
        # 添加图例 - 确保图例颜色与实际方块颜色一致
        reachable_patch = patches.Patch(color='#2ECC71', label='可达')
        unreachable_patch = patches.Patch(color='#E74C3C', label='不可达')
        plt.legend(handles=[reachable_patch, unreachable_patch], loc='lower right', fontsize=12)
        
        # 设置坐标轴
        plt.xlim(-spacing, grid_cols * (box_size + spacing) - spacing)
        plt.ylim(-grid_rows * (box_size + spacing) + spacing, box_size + spacing)
        plt.axis('off')  # 隐藏坐标轴
        
        # 调整布局
        plt.tight_layout()
        
        # 添加统计信息文本
        stats_text = f"总IP数: {total_ips}\n可达IP数: {len(reachable_set)}\n不可达IP数: {total_ips - len(reachable_set)}\n可达率: {len(reachable_set)/total_ips*100:.1f}%"
        plt.text(
            #0.02, 0.98, stats_text, 
            0.79, 0.1, stats_text, 
            transform=ax.transAxes, 
            verticalalignment='top', 
            fontsize=10, 
            bbox=dict[str, str | float](boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        # 显示图形
        plt.show()
        
    except ValueError as e:
        print(f"[错误] 绘制图形失败: {e}")
    except Exception as e:
        print(f"[错误] 绘制图形时发生异常: {e}")

# 主函数
def main():
    if sys.platform.startswith('win'):
        Colors.print_color("╔══════════════════════════════════════════════════════╗", 11)
        Colors.print_color("║                 IP网段扫描工具                      ║", 11)
        Colors.print_color("╚══════════════════════════════════════════════════════╝", 11)
    else:
        print(f"{Colors.CYAN}╔══════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║                 IP网段扫描工具                      ║{Colors.RESET}")
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════════╝{Colors.RESET}")
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='IP网段扫描工具')
    parser.add_argument('-n', '--network', type=str, help='要扫描的IP网段（例如：192.168.1.0/24）')
    parser.add_argument('-t', '--threads', type=int, default=100, help='并发线程数（默认：100）')
    parser.add_argument('-p', '--packets', type=int, default=1, help='每个IP的ping包数量（默认：1）')
    parser.add_argument('-w', '--timeout', type=int, default=500, help='ping超时时间（毫秒，默认：500）')
    parser.add_argument('--no-graph', action='store_true', help='不显示图形化结果')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果提供了命令行参数，则使用参数值；否则，获取用户输入的网段
    if args.network:
        network = args.network
    else:
        network = input("请输入IP网段（例如：192.168.1.0/24）: ")
    
    # 解析网段
    ips = parse_network(network)
    if not ips:
        return
    
    total_ips = len(ips)
    if sys.platform.startswith('win'):
        Colors.print_color(f"\n[信息] 开始扫描网段: {network}", 9)  # 9: 蓝色背景黑色文字
        Colors.print_color(f"[信息] 总共有 {total_ips} 个IP地址需要扫描", 9)
        Colors.print_color(f"[信息] 并发线程数: {args.threads}", 9)
        Colors.print_color(f"[信息] 每个IP的ping包数量: {args.packets}", 9)
        Colors.print_color(f"[信息] ping超时时间: {args.timeout} 毫秒", 9)
        print("\n" + "╔══════════════════════════════════════════════════════╗")
    else:
        print(f"\n{Colors.BLUE}[信息] 开始扫描网段: {network}{Colors.RESET}")
        print(f"{Colors.BLUE}[信息] 总共有 {total_ips} 个IP地址需要扫描{Colors.RESET}")
        print(f"{Colors.BLUE}[信息] 并发线程数: {args.threads}{Colors.RESET}")
        print(f"{Colors.BLUE}[信息] 每个IP的ping包数量: {args.packets}{Colors.RESET}")
        print(f"{Colors.BLUE}[信息] ping超时时间: {args.timeout} 毫秒{Colors.RESET}")
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════╗{Colors.RESET}")
    
    # 初始化结果列表
    reachable_ips = []
    unreachable_ips = []
    lock = threading.Lock()
    
    # 初始化进度计数器
    scanned_count = 0
    progress_lock = threading.Lock()
    
    # 进度回调函数
    def update_progress():
        nonlocal scanned_count
        with progress_lock:
            scanned_count += 1
            progress = scanned_count / total_ips * 100
            # 每扫描10%的IP或扫描完成时显示进度
            if scanned_count % (total_ips // 10 or 1) == 0 or scanned_count == total_ips:
                if sys.platform.startswith('win'):
                    Colors.print_color(f"[进度] 已扫描 {scanned_count}/{total_ips} 个IP地址 ({progress:.1f}%)", 14)  # 14: 黄色背景黑色文字
                else:
                    print(f"{Colors.YELLOW}[进度] 已扫描 {scanned_count}/{total_ips} 个IP地址 ({progress:.1f}%){Colors.RESET}")
    
    start_time = time.time()
    
    # 使用线程池进行并发扫描
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        # 使用lambda函数传递额外参数
        list(executor.map(lambda ip: scan_ip(ip, reachable_ips, unreachable_ips, lock, update_progress, 
                                            count=args.packets, timeout=args.timeout), ips))
    
    end_time = time.time()
    scan_time = end_time - start_time
    
    if sys.platform.startswith('win'):
        print("\n" + "╚══════════════════════════════════════════════════════╝")
        Colors.print_color(f"[完成] 扫描完成！耗时: {scan_time:.2f} 秒", 10)
        Colors.print_color(f"[完成] 平均扫描速度: {total_ips/scan_time:.2f} 个IP/秒", 10)
    else:
        print(f"\n{Colors.CYAN}╚══════════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"{Colors.GREEN}[完成] 扫描完成！耗时: {scan_time:.2f} 秒{Colors.RESET}")
        print(f"{Colors.GREEN}[完成] 平均扫描速度: {total_ips/scan_time:.2f} 个IP/秒{Colors.RESET}")
    
    # 显示结果表格
    show_results_table(reachable_ips, unreachable_ips)
    
    # 绘制图形化结果（如果没有指定--no-graph参数）
    if not args.no_graph:
        plot_ip_status(network, reachable_ips, unreachable_ips)

if __name__ == "__main__":
    main()
