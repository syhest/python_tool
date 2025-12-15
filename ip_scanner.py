import ipaddress
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# 用于存储结果的列表
reachable_ips = []
unreachable_ips = []
lock = threading.Lock()

# ping测试函数
def ping_ip(ip):
    """测试单个IP是否可达"""
    try:
        # 根据操作系统选择ping命令和参数
        if sys.platform.startswith('win'):
            # Windows系统ping命令
            command = ['ping', '-n', '2', '-w', '1000', str(ip)]  # 发送2个包，超时1秒
        else:
            # Linux/macOS系统ping命令
            command = ['ping', '-c', '2', '-W', '1', str(ip)]  # 发送2个包，超时1秒
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False
        )
        
        stdout = result.stdout
        
        # 分析输出内容
        has_reply = "来自" in stdout or "Reply from" in stdout or "64 bytes from" in stdout
        has_ttl = "TTL=" in stdout or "ttl=" in stdout
        has_timeout = "请求超时" in stdout or "Request timed out" in stdout or "timeout" in stdout.lower()
        has_unreachable = "无法访问目标主机" in stdout or "Destination host unreachable" in stdout or "unreachable" in stdout.lower()
        
        # 综合判断是否可达：
        # 1. 必须有TTL值（表示成功收到回复）
        # 2. 不能包含"无法访问目标主机"或"unreachable"
        # 3. 考虑返回码，但优先级低于实际输出内容
        is_reachable = (has_ttl and not has_unreachable) or \
                      (result.returncode == 0 and has_reply and not has_unreachable)
        
        return is_reachable
    except Exception as e:
        return False

# 扫描IP函数
def scan_ip(ip):
    """扫描单个IP并更新结果列表"""
    is_reachable = ping_ip(ip)
    with lock:
        if is_reachable:
            reachable_ips.append(str(ip))
            print(f"[可达] {ip}")
        else:
            unreachable_ips.append(str(ip))
            print(f"[不可达] {ip}")

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
    
    # 显示统计信息表格
    print("\n" + "=" * 60)
    print("扫描结果统计")
    print("=" * 60)
    print(f"| {'统计项':<15} | {'数值':<10} |")
    print(f"|{'-'*17}|{'-'*12}|")
    print(f"| {'总IP数':<15} | {total:<10} |")
    print(f"| {'可达IP数':<15} | {reachable_count:<10} |")
    print(f"| {'不可达IP数':<15} | {unreachable_count:<10} |")
    print(f"| {'可达率':<15} | {reachable_count/total*100:.1f}%{'':<6} |")
    print("=" * 60)
    
    # 显示可达IP表格
    print(f"\n可达IP列表 ({len(reachable_ips)}个):")
    print("-" * 60)
    if reachable_ips:
        # 计算每行显示的IP数量，根据终端宽度调整
        ip_per_row = 5
        rows = (len(reachable_ips) + ip_per_row - 1) // ip_per_row
        
        for i in range(rows):
            start = i * ip_per_row
            end = min((i + 1) * ip_per_row, len(reachable_ips))
            row_ips = reachable_ips[start:end]
            # 格式化输出IP，每个IP占16字符宽度
            formatted_ips = [f"{ip:<16}" for ip in row_ips]
            print("   " + "".join(formatted_ips))
    else:
        print("   无可达IP")
    print("-" * 60)
    
    # 显示不可达IP表格
    print(f"\n不可达IP列表 ({len(unreachable_ips)}个):")
    print("-" * 60)
    if unreachable_ips:
        # 计算每行显示的IP数量
        ip_per_row = 5
        rows = (len(unreachable_ips) + ip_per_row - 1) // ip_per_row
        
        for i in range(rows):
            start = i * ip_per_row
            end = min((i + 1) * ip_per_row, len(unreachable_ips))
            row_ips = unreachable_ips[start:end]
            # 格式化输出IP，每个IP占16字符宽度
            formatted_ips = [f"{ip:<16}" for ip in row_ips]
            print("   " + "".join(formatted_ips))
    else:
        print("   无不可达IP")
    print("-" * 60)

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
        plt.legend(handles=[reachable_patch, unreachable_patch], loc='upper right', fontsize=12)
        
        # 设置坐标轴
        plt.xlim(-spacing, grid_cols * (box_size + spacing) - spacing)
        plt.ylim(-grid_rows * (box_size + spacing) + spacing, box_size + spacing)
        plt.axis('off')  # 隐藏坐标轴
        
        # 调整布局
        plt.tight_layout()
        
        # 添加统计信息文本
        stats_text = f"总IP数: {total_ips}\n可达IP数: {len(reachable_set)}\n不可达IP数: {total_ips - len(reachable_set)}\n可达率: {len(reachable_set)/total_ips*100:.1f}%"
        plt.text(
            0.02, 0.98, stats_text, 
            transform=ax.transAxes, 
            verticalalignment='top', 
            fontsize=10, 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        # 显示图形
        plt.show()
        
    except ValueError as e:
        print(f"[错误] 绘制图形失败: {e}")
    except Exception as e:
        print(f"[错误] 绘制图形时发生异常: {e}")

# 主函数
def main():
    print("=" * 60)
    print("            IP网段扫描工具")
    print("=" * 60)
    
    # 获取用户输入的网段
    network = input("请输入IP网段（例如：192.168.1.0/24）: ")
    
    # 解析网段
    ips = parse_network(network)
    if not ips:
        return
    
    total_ips = len(ips)
    print(f"\n[信息] 开始扫描网段: {network}")
    print(f"[信息] 总共有 {total_ips} 个IP地址需要扫描")
    print("\n" + "=" * 60)
    
    start_time = time.time()
    
    # 使用线程池进行并发扫描
    with ThreadPoolExecutor(max_workers=100) as executor:
        executor.map(scan_ip, ips)
    
    end_time = time.time()
    scan_time = end_time - start_time
    
    print("\n" + "=" * 60)
    print(f"[完成] 扫描完成！耗时: {scan_time:.2f} 秒")
    
    # 显示结果表格
    show_results_table(reachable_ips, unreachable_ips)
    
    # 绘制图形化结果
    plot_ip_status(network, reachable_ips, unreachable_ips)

if __name__ == "__main__":
    main()
