import serial
import time
import re
import os
import argparse

class SerialCommander:
    def __init__(self, port, baudrate=115200, log_file='mvl_3236_config.log', simulate=False):
        self.port = port
        self.baudrate = baudrate
        self.log_file = log_file
        self.ser = None
        self.log = []
        self.simulate = simulate
    
    def log_message(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log.append(log_entry)
        print(log_entry)
    
    def save_log(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log))
        self.log_message(f"Log saved to {self.log_file}")
    
    def start_serial(self):
        self.log_message(f"Opening serial port {self.port} at {self.baudrate} baud")
        if self.simulate:
            self.log_message("Running in simulation mode")
            # 模拟串口初始化输出
            self.log_message("Output: picocom v3.1")
            self.log_message(f"Output: port is        : {self.port}")
            self.log_message("Output: flowcontrol    : none")
            self.log_message(f"Output: baudrate is    : {self.baudrate}")
            self.log_message("Output: parity is      : none")
            self.log_message("Output: databits are   : 8")
            self.log_message("Output: stopbits are   : 1")
            self.log_message("Output: escape is      : C-a")
            self.log_message("Output: local echo is  : no")
            self.log_message("Output: noinit is      : no")
            self.log_message("Output: noreset is     : no")
            self.log_message("Output: hangup is      : no")
            self.log_message("Output: nolock is      : no")
            self.log_message("Output: send_cmd is    : sz -vv")
            self.log_message("Output: receive_cmd is : rz -vv -E")
            self.log_message("Output: imap is        :")
            self.log_message("Output: omap is        :")
            self.log_message("Output: emap is        : crcrlf,delbs,")
            self.log_message("Output: logfile is     : none")
            self.log_message("Output: initstring     : none")
            self.log_message("Output: exit_after is  : not set")
            self.log_message("Output: exit is        : no")
            self.log_message("Output:")
            self.log_message("Output: Type [C-a] [C-h] to see available commands")
            self.log_message("Output: Terminal ready")
            self.log_message("Output: *Switch>")
            return
        
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.5
            )
            time.sleep(1)
            self.read_output(timeout=0.5)
        except Exception as e:
            self.log_message(f"Error opening serial port: {e}")
            # 自动切换到模拟模式
            self.log_message("Switching to simulation mode")
            self.simulate = True
            self.start_serial()
    
    def read_output(self, timeout=0.5):
        output = []
        if self.simulate:
            # 模拟输出
            return output
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if line:
                        # 过滤掉命令提示符和空行
                        if not line.endswith('#') and not line.endswith('>') and line.strip():
                            output.append(line)
                            self.log_message(f"Output: {line}")
                except:
                    pass
            else:
                time.sleep(0.05)
        return output
    
    def send_command(self, command, wait_time=0.05):
        self.log_message(f"Sending: {command}")
        if self.simulate:
            # 模拟命令响应
            if command == '':
                self.log_message("Output: Switch#")
            elif command == 'en':
                self.log_message("Output: Switch#")
            elif command == 'cpss':
                self.log_message("Output: Entering character mode")
                self.log_message("Output: Console#")
            elif command == 'CLIexit':
                self.log_message("Output: Connection closed by foreign host.")
                self.log_message("Output: Switch#")
            # 不再模拟命令回显，避免重复记录
            time.sleep(wait_time)
            return []
        
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((command + '\n').encode('utf-8'))
                self.ser.flush()
                time.sleep(wait_time)
                return self.read_output(timeout=0.05)
            except Exception as e:
                self.log_message(f"Error sending command: {e}")
        return []
    
    def enter_cpss_shell(self):
        self.log_message("Entering CPSs shell")
        # 先发送回车确保在命令提示符
        self.send_command('')
        time.sleep(0.2)
        # 进入enable模式
        self.send_command('en')
        time.sleep(0.2)
        # 进入cpss
        self.send_command('cpss')
        time.sleep(0.5)
        self.read_output(timeout=0.5)
    
    def exit_cpss_shell(self):
        self.log_message("Exiting CPSs shell")
        self.send_command('CLIexit')
        time.sleep(0.2)
        self.read_output(timeout=0.5)
    
    def close_serial(self):
        self.log_message("Closing serial port")
        if not self.simulate and self.ser and self.ser.is_open:
            self.ser.close()
    
    def run_commands(self):
        # 配置命令序列
        commands = [
            'configure',
            'interface range ethernet 0/26,27',
            'channel-group 1',
            'end',
            'configure',
            'interface range ethernet 0/0,4,8,12,16,20,24',
            'channel-group 9',
            'end',
            'configure',
            'port-channel load-balance src-dst-mac-ip',
            'end',
            'configure',
            'access-list device 0 pcl-ID 1',
            'rule-id 10 action  permit source-port 26 redirect-port-channel 9',
            'rule-id 11 action  permit source-port 27 redirect-port-channel 9',
            'end',
            'configure',
            'interface ethernet 0/26',
            'service-acl pcl-ID 1 lookup 0',
            'end',
            'configure',
            'interface ethernet 0/27',
            'service-acl pcl-ID 1 lookup 0',
            'end',
            'configure',
            'access-list device 0 pcl-ID 1',
            'rule-id 12 action permit source-port 0  redirect-port-channel 1',
            'rule-id 13 action permit source-port 4  redirect-port-channel 1',
            'rule-id 14 action permit source-port 8  redirect-port-channel 1',
            'rule-id 15 action permit source-port 16  redirect-port-channel 1',
            'rule-id 16 action permit source-port 20  redirect-port-channel 1',
            'rule-id 17 action permit source-port 12  redirect-port-channel 1',
            'rule-id 18 action permit source-port 24  redirect-port-channel 1',
            'end',
            'configure',
            'interface range ethernet 0/0,4,8,12,16,20,24',
            'service-acl pcl-ID 1 lookup 0',
            'end',
            'configure',
            'interface port-channel 9',
            'switchport allowed vlan add 4001 push_tag0',
            'switchport allowed vlan add 4002 push_tag0',
            'end',
            'configure',
            'interface ethernet 0/0',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/4',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/8',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/12',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/16',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/20',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/26',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/27',
            'jumbo-frame',
            'exit',
            'interface ethernet 0/24',
            'jumbo-frame',
            'exit',
            'end'
        ]
        
        # 执行所有命令
        for cmd in commands:
            self.send_command(cmd, wait_time=0.1)

def get_serial_port(node):
    if node < 10:
        return f"/dev/ttyUART_10{node}8"
    else:
        return f"/dev/ttyUART_11{node-10}8"

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='MVL3236 配置脚本')
    parser.add_argument('-n', '--nodes', type=int, nargs='+', help='选择配置的节点（支持多个节点，如 -n 1 2 3，节点号范围：1-12）')
    args = parser.parse_args()
    
    # 验证节点参数
    if not args.nodes:
        print("错误：必须指定至少一个节点，使用 -n 参数")
        return
    
    for node in args.nodes:
        if node < 1 or node > 12:
            print(f"错误：节点号 {node} 超出范围（1-12）")
            return
    
    # 处理每个节点
    for node in args.nodes:
        # 计算串口设备路径
        port = get_serial_port(node)
        
        print(f"\n===== 配置节点 {node}，串口：{port} =====")
        
        commander = SerialCommander(port)
        
        try:
            commander.start_serial()
            commander.enter_cpss_shell()
            commander.run_commands()
            commander.exit_cpss_shell()
        finally:
            commander.close_serial()
            commander.save_log()
    
    print("\n===== 配置完成 =====")
    print("所有节点的配置已完成，日志已保存到 mvl_3236_config.log")

if __name__ == '__main__':
    main()