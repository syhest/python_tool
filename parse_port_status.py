#!/usr/bin/env python3

import os
import re

def parse_all_port_status(log_file, target_ports):
    """
    解析日志文件中的所有端口状态记录
    :param log_file: 日志文件路径
    :param target_ports: 要查询的端口列表
    :return: 所有记录的端口状态列表
    """
    # 检查文件是否存在
    if not os.path.exists(log_file):
        print(f"错误：文件 {log_file} 不存在")
        return None
    
    # 读取日志文件
    with open(log_file, 'r') as f:
        content = f.read()
    
    # 查找所有端口状态记录
    # 每个记录包含"循环次数:"、"执行时间:"、"Dev/Port:"和"Link:"行
    all_records = []
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
    
    if not all_records:
        print("错误：未找到端口状态记录")
        return None
    
    return all_records

def main():
    # 日志文件路径
    log_file = os.path.join(os.getcwd(), 'test.log')
    
    # 目标端口
    target_ports = ['0/24', '0/25']
    
    # 解析所有端口状态记录
    all_records = parse_all_port_status(log_file, target_ports)
    
    if all_records:
        print("端口状态解析结果（所有记录）：")
        print("=" * 60)
        print(f"{'循环次数':<10}{'执行时间':<25}{'端口0/24状态':<15}{'端口0/25状态':<15}")
        print("=" * 60)
        
        for record in all_records:
            port_24_status = record['port_status'].get('0/24', '未找到')
            port_25_status = record['port_status'].get('0/25', '未找到')
            print(f"{record['cycle']:<10}{record['time']:<25}{port_24_status:<15}{port_25_status:<15}")
        
        print("=" * 60)
        print(f"总计 {len(all_records)} 条记录")

if __name__ == "__main__":
    main()
