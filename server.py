#!/usr/bin/python3

import os
import hashlib
import json
from socket import socket, AF_INET, SOCK_STREAM
import time
import sys
import argparse
import random

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
                time.strftime('%F %T', time.localtime()),
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
                '%s, [info], msg:client connected to port %s from %s:%s\r\n' % (
                    time.strftime('%F %T', time.localtime()),
                    PORT,
                    client_addr[0],
                    client_addr[1]
                )
            )
            try:
                # metadata str
                recv_str = client_socket.recv(1024)
                file_metadata = json.loads(recv_str.decode())
                file_metadata['ip'] = client_addr[0]
                full_path_filename = self.valid_file(file_metadata)
            except:
                sys.stdout.write(
                    '%s, [error], msg:%s illegal request\r\n' % (
                        time.strftime('%F %T', time.localtime()),
                        client_addr[0]
                    )
                )

            # valid file meta data success, got backup file full path
            if file_metadata:
                if full_path_filename:
                    # send 'ok' to client, tell client start send file content data to this server
                    client_socket.send('ok'.encode())
                    rand_str = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789',5))
                    temp_file = '/tmp/scc_%s.dat' % rand_str
                    fp = open(temp_file, 'ab+')
                    # loop read client send data
                    while True:
                        try:
                            d = client_socket.recv(1024)
                        except:
                            break
                            fp.close()

                        if d:
                            fp.write(d)
                        else:
                            fp.close()
                            break
                    if fp:
                        fp.close()
                    # valid receive data md5 value
                    # if pass then remove to destination directory
                    if self.get_file_md5(temp_file) == file_metadata['hash']:
                        os.rename(temp_file, full_path_filename)
                        noti_msg = '%s, [info], msg:%s %s config file backup success\r\n' % (
                            time.strftime('%F %T', time.localtime()),
                            client_addr[0],
                            file_metadata['full_path_filename']
                        )
                    # valid receive data failed, delete tmp file
                    else:
                        noti_msg = '%s, [warning], msg:%s %s receive data hash verify failed!\r\n' % (
                            time.strftime('%F %T', time.localtime()),
                            client_addr[0],
                            file_metadata['full_path_filename']
                        )
                        os.remove(temp_file)
                    sys.stdout.write(noti_msg)
                # local already exist this config file copy, tell client don't send data
                else:
                    client_socket.send('no'.encode())
                    noti_msg = '%s, [info], from:%s, file:%s, msg:file is already exist on the local\r\n' % (
                        time.strftime('%F %T', time.localtime()),
                        client_addr[0],
                        file_metadata['full_path_filename']
                    )
                    sys.stdout.write(noti_msg)
            # client_socket.shutdown(2)
            client_socket.close()

    def valid_file(self, data):
        ip_path = data['ip']
        filename_datetime = data['date'].replace(':', '_').replace(' ', '_').replace('-', '_')
        dest_hash = data['hash']
        filename = data['filename']
        x = filename.split('.')
        filename_ext = x[0] if len(x) == 1 else x[-1]
        filename_name = x[0] if len(x) == 1 else '.'.join(x[0:-1])

        backup_abs_path = os.path.join(DATA_DIR, ip_path, filename_name)
        filename_full_path = os.path.join(backup_abs_path, filename)

        file_path_state_code = self.verify_directory(backup_abs_path)
        if '0x00' != file_path_state_code:
            os.makedirs(backup_abs_path)
            sys.stdout.write(
                '%s, [info], msg:create directory %s\r\n' % (
                    time.strftime('%F %T', time.localtime()),
                    backup_abs_path
                )
            )

        origin_md5 = self.get_file_md5(filename_full_path)
        # print(origin_md5, '------', dest_hash)
        if origin_md5 == dest_hash:
            return False

        if os.path.exists(filename_full_path) and os.path.isfile(filename_full_path) and origin_md5 != dest_hash:
            os.rename(filename_full_path, '%s/%s_%s.%s' % (
                backup_abs_path,
                filename_name,
                filename_datetime,
                filename_ext
            ))

        return filename_full_path

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
