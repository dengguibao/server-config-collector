#!/usr/bin/python3

from socket import socket, AF_INET, SOCK_STREAM
import time
import uuid
import os
import hashlib
import json
import sys
import argparse

SERVER = '127.0.0.1'
PORT = '2615'
DELAY = 5
FILE_PATH = 'files.conf'
MAX_SIZE = 1 * 1024 * 1024

hash_array = {

}


class Client:
    ERR = {
        '0x00': 'success',
        '0x01': 'file not read',
        '0x02': 'file not exist',
        '0x03': 'path is directory',
        '0x99': 'unknown error'
    }

    def __init__(self):
        self.tcp_socket = socket(AF_INET, SOCK_STREAM)

        file_path_state_code = self.verify_file(FILE_PATH)
        if '0x00' != file_path_state_code:
            sys.stdout.write('%s, [error], reason:config file error, %s\r\n' % (
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                self.ERR[file_path_state_code]
            ))
            exit()

    def run(self):
        # self.tcp_socket.connect((SERVER, PORT))
        # threading.Thread(target=self.print_receive_msg, args=()).start()

        with open(FILE_PATH) as fp:
            all_lines = fp.read()
        data = []
        for l in all_lines.splitlines():
            line = l.strip()
            if len(line) == 0 or line[0:1] == '#':
                continue
            else:
                data.append(line)
        if len(data) > 0:
            self.process(data)
        else:
            sys.stdout.write('%s, [info], info:backup file list is empty\r\n' % (
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            ))

    def print_receive_msg(self):
        while True:
            data = self.tcp_socket.recv(1024)
            sys.stdout.write(
                '%s, [info], info:%s' % (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    data.decode()
                )
            )

    def process(self, file_list):
        for f in file_list:
            state_code = self.verify_file(f)
            if state_code != '0x00':
                sys.stdout.write('%s, [error], filename:%s, reason:%s\r\n' % (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    f,
                    self.ERR[state_code]
                ))
                continue
            file_path_uuid = ''.join(
                str(uuid.uuid5(uuid.NAMESPACE_DNS, f)).split('-')
            )
            file_hash = self.get_file_md5(f)
            date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            file_content = self.get_file_content(f)
            if not file_content:
                continue
            # print(file_path_uuid, file_hash)
            if file_path_uuid not in hash_array or hash_array[file_path_uuid] != file_hash:
                hash_array[file_path_uuid] = file_hash
                data = {
                    'full_path_filename': f,
                    'hash': file_hash,
                    'date': date_time,
                    'content': file_content,
                    'filename': os.path.split(f)[1]
                }
                self.tcp_socket.connect((SERVER, PORT))
                self.tcp_socket.sendall(json.dumps(data, ensure_ascii=False).encode())
                sys.stdout.write('%s, [info], filename:%s, info:push to server\r\n' % (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    f
                ))
            else:

                continue

    @staticmethod
    def get_file_content(filename):
        if os.path.exists(filename) and os.path.isfile(filename):
            with open(filename, 'r') as fp:
                data = fp.read()
            return data
        return False

    @staticmethod
    def verify_file(filename):
        if not os.path.exists(filename):
            return '0x02'
        if not os.path.isfile(filename):
            return '0x03'
        if not os.access(filename, os.R_OK):
            return '0x01'
        file_size = os.path.getsize(filename)
        if 0 < file_size < MAX_SIZE:
            return '0x00'
        return '0x99'

    @staticmethod
    def get_file_md5(filename):
        if not os.path.exists(filename) and not os.path.isfile(filename):
            return
        with open(filename, 'rb') as fp:
            data = fp.read()

        return hashlib.md5(data).hexdigest()


if __name__ == '__main__':
    av = sys.argv[1:]
    if not len(av):
        av.append('-h')

    parser = argparse.ArgumentParser(description='config file auto backup client program')

    parser.add_argument('--port', type=int, default=2615, help='listen port, default 2615')
    parser.add_argument('--delay', type=int, default=5, help='pool delay, default 5s')
    parser.add_argument('--max-size', type=int, default=1, help='backup file max size, default 1M')
    parser.add_argument('--files', type=str, default='./files.conf', help='backup files list, per line a file path, default ./files.conf')
    parser.add_argument('--server', type=str, required=True, help="server address")

    # sub_parser = parser.add_subparsers(description='test')
    # test_parser = sub_parser.add_parser('test', help='aaaa')
    # test_parser.add_argument('-test', help='test')

    args = parser.parse_args(av)

    SERVER = args.server
    PORT = args.port
    DELAY = args.delay
    FILE_PATH = args.files
    MAX_SIZE = args.max_size * 1024 * 1024

    while True:
        try:
            client = Client()
            client.run()
            time.sleep(DELAY)
        except:
            break
