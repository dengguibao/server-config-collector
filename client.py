#!/usr/bin/python3

from socket import socket, AF_INET, SOCK_STREAM
import time
import uuid
import os
import hashlib
import json
import sys
import argparse
import glob
import threading

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
        '0x99': 'file is empty or more than max size'
    }

    def __init__(self):
        # self.tcp_socket = socket(AF_INET, SOCK_STREAM)
        # self.tcp_socket.connect((SERVER, PORT))

        file_path_state_code = self.verify_file(FILE_PATH)
        if '0x00' != file_path_state_code:
            sys.stdout.write('%s, [error], msg:config file error, %s\r\n' % (
                time.strftime('%F %T', time.localtime()),
                self.ERR[file_path_state_code]
            ))
            exit()

    def run(self):
        with open(FILE_PATH) as fp:
            all_lines = fp.read()
        file_list = []
        for l in all_lines.splitlines():
            line = l.strip()

            if len(line) == 0 or line[0:1] == '#':
                continue
            else:
                for i in glob.glob(line):
                    threading.Thread(target=self.process, args=(i,)).start()

        # if len(file_list) == 0:
        #     sys.stdout.write('%s, [info], msg:backup file list is empty\r\n' % (
        #         time.strftime('%F %T', time.localtime()),
        #     ))
        # else:
        #     for i in file_list:
        #         threading.Thread(target=self.process, args=(i,)).start()
        while True:
            if threading.active_count() == 1:
                break

    def process(self, filename):
        f = filename
        state_code = self.verify_file(f)
        if state_code != '0x00':
            sys.stdout.write('%s, [error], filename:%s, msg:%s\r\n' % (
                time.strftime('%F %T', time.localtime()),
                f,
                self.ERR[state_code]
            ))
            return

        file_path_uuid = ''.join(
            str(uuid.uuid5(uuid.NAMESPACE_DNS, f)).split('-')
        )
        file_hash = self.get_file_md5(f)

        if file_path_uuid not in hash_array or hash_array[file_path_uuid] != file_hash:
            hash_array[file_path_uuid] = file_hash
            # send file metadata info
            metadata_info = self.build_file_metadata_info(f)
            # if socket is close, connect to server
            # if getattr(self.tcp_socket, '_closed'):
            #     self.tcp_socket = socket(AF_INET, SOCK_STREAM)
            #     self.tcp_socket.connect((SERVER, PORT))
            try:
                tcp_socket = socket(AF_INET, SOCK_STREAM)
                tcp_socket.connect((SERVER, PORT))
            except:
                sys.stdout.write('connect to server failed!\r\n')
                return
            tcp_socket.sendall(json.dumps(metadata_info, ensure_ascii=False).encode())
            max_wait_time = 0

            # if receive success then send data to server
            while True:
                server_response = tcp_socket.recv(1024)
                if server_response or max_wait_time > 1:
                    break
                time.sleep(.1)
                max_wait_time += .1

            if server_response.decode() == 'ok':
                file_data = self.get_file_content(f)
                for i in file_data:
                    tcp_socket.send(i)

                sys.stdout.write('%s, [info], filename:%s, msg:push to server\r\n' % (
                    time.strftime('%F %T', time.localtime()),
                    f
                ))
            tcp_socket.close()

    @staticmethod
    def get_file_content(filename):
        data = []
        with open(filename, 'rb') as fp:
            while True:
                content = fp.read(1024)
                if content:
                    data.append(content)
                else:
                    break
        return data

    def build_file_metadata_info(self, filename):
        file_hash = self.get_file_md5(filename)
        date_time = time.strftime('%F %T', time.localtime())
        data = {
            'full_path_filename': filename,
            'hash': file_hash,
            'date': date_time,
            'filename': os.path.split(filename)[1]
        }
        return data

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
        if not os.path.exists(filename) or not os.path.isfile(filename) or os.path.getsize(filename) <= 0:
            return False

        m = hashlib.md5()
        with open(filename, 'rb') as fp:
            while True:
                data = fp.read(4096)
                if not data:
                    break
                m.update(data)
        file_hash_str = m.hexdigest()
        return file_hash_str


if __name__ == '__main__':
    av = sys.argv[1:]
    if not len(av):
        av.append('-h')

    parser = argparse.ArgumentParser(description='config file auto backup client program')

    parser.add_argument('--port', type=int, default=2615, help='listen port, default 2615')
    parser.add_argument('--delay', type=int, default=5, help='scan frequency, default 5s')
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

    client = Client()
    while True:
        try:
            client.run()
            time.sleep(DELAY)
        except OSError as e:
            print(e)
            break
