#!/usr/bin/python3

import os
import hashlib
import json
from socket import socket, AF_INET, SOCK_STREAM
import time
import sys
import argparse

DATA_DIR = './'
HOST = '0.0.0.0'
PORT = 2615
MAX_CONNECTION = 200


class Server:
    ERR = {
        '0x00': 'success',
        '0x01': 'path not exist',
        '0x02': 'path not directory',
        '0x03': 'path is not writeable',
        '0x99': 'unknown error'
    }

    def __init__(self):
        data_dir_state_code = self.verify_directory(DATA_DIR)
        if '0x00' != data_dir_state_code:
            sys.stdout.write('%s, [error], reason:%s\r\n' % (
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                self.ERR[data_dir_state_code]
            ))
            return

        self.tcp_server = socket(AF_INET, SOCK_STREAM)
        self.tcp_server.bind((HOST, PORT))
        self.tcp_server.listen(MAX_CONNECTION)
        sys.stdout.write("[*] Accepted connection from: %s:%d\r\n" % (HOST, PORT))

    def run(self):
        while True:
            client_socket, client_addr = self.tcp_server.accept()
            # client connected
            sys.stdout.write(
                '%s, [info], info:client connected to port %s from %s:%s\r\n' % (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    PORT,
                    client_addr[0],
                    client_addr[1]
                )
            )
            # metadata str
            recv_metadata_str = client_socket.recv(1024)
            try:
                file_metadata = json.loads(recv_metadata_str.decode())
                file_metadata['ip'] = client_addr[0]
                full_path_filename = self.valid_file(file_metadata)
            except:
                sys.stdout.write(
                    '%s, [error], info:%s illegal request\r\n' % (
                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                        client_addr[0]
                    )
                )

            # valid success
            if file_metadata:
                if full_path_filename:
                    # send 'ok' to client, tell client start post file content to server
                    client_socket.send('ok'.encode())
                    fp = open(full_path_filename, 'ab+')
                    d = b''
                    while True:
                        try:
                            d = client_socket.recv(1024)
                        except:
                            fp.close()

                        if d:
                            fp.write(d)
                        else:
                            fp.close()
                            break
                    noti_msg = '%s, [info], info:%s %s config file backup success\r\n' % (
                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                        client_addr[0],
                        file_metadata['full_path_filename']
                    )
                    sys.stdout.write(noti_msg)
                else:
                    client_socket.send('no'.encode())
                    noti_msg = '%s, [info], info:config file[%s %s] is already exist on the local\r\n' % (
                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                        client_addr[0],
                        file_metadata['full_path_filename']
                    )
                    sys.stdout.write(noti_msg)

            client_socket.shutdown(2)
            client_socket.close()

    def valid_file(self, data):
        ip_path = data['ip'].replace('.', '-')
        date_path = data['date'].split(' ')[0]
        date_ext = data['date'].split(' ')[1].replace(':', '_')
        dest_hash = data['hash']
        filename = data['filename']

        file_path = os.path.join(DATA_DIR, ip_path, date_path)
        full_path_filename = os.path.join(file_path, filename)

        file_path_state_code = self.verify_directory(file_path)
        if '0x00' != file_path_state_code:
            os.makedirs(file_path)
            sys.stdout.write(
                '%s, [info], info:create directory %s\r\n' % (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    file_path
                )
            )

        origin_md5 = self.get_file_md5(full_path_filename)
        # print(origin_md5, '------', dest_hash)
        if origin_md5 == dest_hash:
            return False

        if os.path.exists(full_path_filename) and os.path.isfile(full_path_filename) and origin_md5 != dest_hash:
            os.rename(full_path_filename, full_path_filename + '.' + date_ext)

        return full_path_filename



    @staticmethod
    def verify_directory(file_path):
        if not os.path.exists(file_path):
            return '0x01'
        if not os.path.isdir(file_path):
            return '0x02'
        if not os.access(file_path, os.W_OK):
            return '0x03'

        return '0x00'

    @staticmethod
    def get_file_md5(filename):
        if not os.path.exists(filename) or not os.path.isfile(filename) or os.path.getsize(filename) == 0:
            return ''
        with open(filename, 'rb') as fp:
            data = fp.read()

        file_hash_str = hashlib.md5(data).hexdigest()
        return file_hash_str


if __name__ == '__main__':
    av = sys.argv[1:]
    if not len(av):
        av.append('-h')

    parser = argparse.ArgumentParser(description='config file auto backup server program')
    parser.add_argument('--host', type=str, default='0.0.0.0', help="listen host address, default 0.0.0.0")
    parser.add_argument('--port', type=int, default=2615, help='listen port, default 2615')
    parser.add_argument('--max-connection', type=int, default=200, help='max connection numbers, default 200')

    parser.add_argument('--data-dir', type=str, help='data save directory, ensure the directory is writeable',
                        required=True)
    args = parser.parse_args(av)

    MAX_CONNECTION = args.max_connection
    DATA_DIR = args.data_dir
    HOST = args.host
    PORT = args.port

    server = Server()
    server.run()
