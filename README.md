# config collect program
## usage
### server
> server.py --data-dir /home/test
  
more info ./server.py -h 
### client
first create a backup files list
>touch files.conf

and then start client
>client.py  --server 127.0.0.1
  
more info ./client.py -h
## systemd
### server  
```bash
PROJECT_DIR=/your server.py/file/path
HOME=${~}
cat > /etc/systemd/system/scc-server.service<<EOF
[Unit]
Description=scc server daemon

[Service]
StandardOutput=syslog
ExecStart=/usr/bin/python3 ${PROJECT_DIR}/server.py --data-dir ${HOME} 
KillSignal=SIGQUIT
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```
### client  
```bash
PROJECT_DIR=/your client.py/file/path
SERVER_IP=YOUR.IP.ADDRESS.

cat > /etc/systemd/system/scc-client.service<<EOF
[Unit]
Description=scc client daemon

[Service]
ExecStart=/usr/bin/python3 ${PROJECT_DIR}/client.py --server ${SERVER_IP} 
StandardOutput=SIGQUIT
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```
