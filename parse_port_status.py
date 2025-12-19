#!/usr/bin/env python3

import os
import re
import argparse

def parse_all_port_status(log_file, target_ports):
    """
    解析日志文件中的所有端口状态记录
    :param log_file: 日志文件路径
    :param target_ports: 要查询的端口列表
    :return: 所有记录的端口状态列表和统计信息
    """
    # 检查文件是否存在
    if not os.path.exists(log_file):
        print(f"错误：文件 {log_file} 不存在")
        return None, None
    
    # 读取日志文件
    with open(log_file, 'r') as f:
        content = f.read()
    
    # 查找所有端口状态记录
    # 每个记录包含"循环次数:"、"执行时间:"、"Dev/Port:"和"Link:"行
    all_records = []
    
    # 初始化统计信息
    port_stats = {}
    for port in target_ports:
        port_stats[port] = {'up': 0, 'down': 0, 'not_found': 0}
    
    for match in re.finditer(r'循环次数: (\d+)\n执行时间: (.*?)\nDev/Port: (.*?)\nLink: (.*?)\n', content, re.DOTALL):
        # 解析端口和状态
        ports = match.group(3).strip().split()
        links = match.group(4).strip().split()
        
        # 创建端口到状态的映射
        port_status = {}
        for port, status in zip(ports, links):
            if port in target_ports:
                port_status[port] = status
        
        # 添加记录
        all_records.append({
            'cycle': int(match.group(1)),
            'time': match.group(2),
            'port_status': port_status
        })
        
        # 更新统计信息
        for port in target_ports:
            status = port_status.get(port, 'not_found')
            if status.lower() == 'up':
                port_stats[port]['up'] += 1
            elif status.lower() == 'down':
                port_stats[port]['down'] += 1
            else:
                port_stats[port]['not_found'] += 1
    
    if not all_records:
        print("错误：未找到端口状态记录")
        return None, None
    
    return all_records, port_stats

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='解析test.log文件中的端口link状态')
    
    # 添加端口参数，允许用户指定要查询的端口
    parser.add_argument('-p', '--ports', nargs='+', default=['0/24', '0/25'],
                       help='要查询的端口列表，默认查询0/24和0/25端口')
    
    # 添加日志文件参数
    parser.add_argument('-f', '--file', default=os.path.join(os.getcwd(), 'test.log'),
                       help='日志文件路径，默认使用当前目录下的test.log')
    
    # 解析参数
    args = parser.parse_args()
    
    # 目标端口
    target_ports = args.ports
    
    # 日志文件路径
    log_file = args.file
    
    # 解析所有端口状态记录和统计信息
    all_records, port_stats = parse_all_port_status(log_file, target_ports)
    
    if all_records and port_stats:
        print("端口状态解析结果（所有记录）：")
        print("=" * (60 + len(target_ports) * 15))
        
        # 构建表头
        header = f"{'循环次数':<10}{'执行时间':<25}"
        for port in target_ports:
            header += f"{'端口' + port + '状态':<15}"
        print(header)
        print("=" * (60 + len(target_ports) * 15))
        
        # 打印所有记录
        for record in all_records:
            row = f"{record['cycle']:<10}{record['time']:<25}"
            for port in target_ports:
                port_status = record['port_status'].get(port, '未找到')
                row += f"{port_status:<15}"
            print(row)
        
        print("=" * (60 + len(target_ports) * 15))
        print(f"总计 {len(all_records)} 条记录")
        
        # 打印统计信息
        print("\n端口状态统计：")
        print("=" * 60)
        for port in target_ports:
            stats = port_stats[port]
            print(f"端口 {port}：")
            print(f"  Up 次数：{stats['up']} 次")
            print(f"  Down 次数：{stats['down']} 次")
            print(f"  未找到次数：{stats['not_found']} 次")
            print(f"  正常率：{stats['up'] / len(all_records) * 100:.2f}%")
        print("=" * 60)

if __name__ == "__main__":
    main()
