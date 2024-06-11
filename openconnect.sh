#!/bin/bash
#**************************************
#Bash Script By digitald.tech
#------------------------------------
# Tested on Ubuntu 18.04 LTS.
# Rev. 1 20-March-2020
#**************************************
currentscript="$0"
function finish {
	clear
	status=$(systemctl is-active --quiet ocserv && echo ahm)
	if [[ "$status" =~ (ahm) ]]; then
   echo "Server Setup Has Been Successfully ✔️ ✔️ ✔️";systemctl status ocserv --no-pager;shred -u ${currentscript};
   echo $OS
else
    echo "Server setup has been failed | unknow error ❌ ❌ ❌	";systemctl status ocserv --no-pager;shred -u ${currentscript};
fi

}


task0() {
if [[ $UID -ne 0 ]]; then
    echo "$0 must be run as root";exit 1
else
    task1;
fi
}

task1() {


if [[ "$OS" =~ (centos) ]]; then
			#centos
			echo "Installing packages";
			yum -y update;
			yum install unzip -y;
			yum install wget -y;
			sudo dnf install -y epel-release
			sudo dnf install -y ocserv
			systemctl enable ocserv;
			systemctl start ocserv;
			
else
			
			#debian
			echo "Installing packages";
			apt update;
			apt install unzip -y;
			apt install wget -y;
			apt install software-properties-common -y;
			apt install ocserv -y;
			systemctl start ocserv;
			apt update;

		fi
		task1_1;
}

task1_1() {
mv /etc/ocserv/ocserv.conf /etc/ocserv/....;
mv /etc/ocserv/ocpasswd /etc/ocserv/.....;
cat << _EOF_ > /etc/ocserv/ocserv.conf
tcp-port = 443
udp-port = 443
#listen-proxy-proto = true
#listen-host = 127.0.0.1
run-as-user = nobody
run-as-group = daemon

socket-file = /var/run/ocserv-socket

ca-cert = /etc/ssl/certs/ssl-cert-snakeoil.pem

isolate-workers = true
max-clients = 0
max-same-clients = 1000000
keepalive = 32400
dpd = 440
mobile-dpd = 1800
try-mtu-discovery = true
cert-user-oid = 0.9.2342.19200300.100.1.1
compression = true
no-compress-limit = 50
auth-timeout = 40
min-reauth-time = 1
max-ban-score = 0
ban-reset-time = 300
cookie-timeout = 300
cookie-rekey-time = 14400
deny-roaming = false
rekey-time = 172800
rekey-method = ssl
tls-priorities = "PERFORMANCE:%SERVER_PRECEDENCE:%COMPAT:-VERS-SSL3.0"
use-utmp = true
use-occtl = true
pid-file = /var/run/ocserv.pid
dtls-legacy = true
device = vpns
predictable-ips = true
default-domain = example.com
ipv4-network = 191.10.10.0/21
#ipv4-netmask = 255.255.221.0
tunnel-all-dns = true
ping-leases = false
cisco-client-compat = true
auth = "plain[passwd=/etc/ocserv/ocpasswd]"
dns = 8.8.8.8
dns = 8.8.4.4
_EOF_

echo "server-cert = /etc/ocserv/.fullchain.pem" >> /etc/ocserv/ocserv.conf;
echo "server-key = /etc/ocserv/.privkey.pem" >> /etc/ocserv/ocserv.conf;
systemctl restart ocserv;

cp /lib/systemd/system/ocserv.service /etc/systemd/system/ocserv.service
sed -i "5 s/^/#/" /etc/systemd/system/ocserv.service;
sed -i "15 s/^/#/" /etc/systemd/system/ocserv.service;

if grep -Fxq "net.ipv4.ip_forward = 1" /etc/sysctl.conf; then
echo "Skipping IP Forwarding"; else
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf; sysctl -p; fi

systemctl daemon-reload;
systemctl stop ocserv.socket;
systemctl disable ocserv.socket;
systemctl restart ocserv.service;
touch /etc/ocserv/ocpasswd;
echo
main_interface=$(ip route get 8.8.8.8 | awk -- '{printf $5}')
iptables -t nat -A POSTROUTING -o $main_interface -j MASQUERADE;
iptables -I INPUT -p tcp --dport 443 -j ACCEPT;
iptables -I INPUT -p udp --dport 443 -j ACCEPT;
iptables-save > /etc/iptables.rules;
cat << _EOF_ > /etc/systemd/system/iptables-restore.service
[Unit]
Description=Packet Filtering Framework
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
ExecStart=/sbin/iptables-restore /etc/iptables.rules
ExecReload=/sbin/iptables-restore /etc/iptables.rules
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
_EOF_
systemctl daemon-reload;
systemctl enable iptables-restore;
task2;
}

task2() {
echo "Updating /etc/ocserv/ocpasswd permission";
touch /etc/ocserv/ocpasswd;
chmod 777 /etc/ocserv/ocpasswd;
task3;
}

task3() {

			if [[ "$OS" =~ (centos) ]]; then
			#centos
			rm /etc/ocserv/.fullchain.pem -f
			rm /etc/ocserv/.privkey.pem -f
			rm /etc/ocserv/cert.zip -f
			sleep 5
			content="https://raw.githubusercontent.com/dtechdevelopers07/gullgull/master/cert.zip"
			sudo wget --no-check-certificate --content-disposition "${content}" -O /etc/ocserv/cert.zip
			chmod 777 /etc/ocserv/cert.zip
			cd /etc/ocserv
			sudo unzip -P vkrc4c9UwvbKvPw9gFsL cert.zip
			mv fullchain.pem .fullchain.pem
			mv privkey.pem .privkey.pem
			rm /etc/ocserv/cert.zip -f
			
else
			
			#debian
			rm /etc/ocserv/.fullchain.pem
			rm /etc/ocserv/.privkey.pem
			rm /etc/ocserv/cert.zip
			content="https://raw.githubusercontent.com/dtechdevelopers07/gullgull/master/cert.zip";
			wget --no-check-certificate --content-disposition "${content}" -O /etc/ocserv/cert.zip;
			chmod 777 /etc/ocserv/cert.zip
			cd /etc/ocserv
			sudo unzip -P vkrc4c9UwvbKvPw9gFsL cert.zip
			mv fullchain.pem .fullchain.pem
			mv privkey.pem .privkey.pem
			rm /etc/ocserv/cert.zip


		fi


chmod 777 /etc/ocserv/.fullchain.pem
chmod 777 /etc/ocserv/.privkey.pem
systemctl restart ocserv
cd
task4;
}

task4() {
echo "Updating Timezone";
cp /usr/share/zoneinfo/Asia/Karachi /etc/localtime;
echo "Server Setup Successfully!"
trap finish EXIT

}

. /etc/os-release

if [[ "$ID" =~ (centos) ]]; then
	OS="centos" 
else
	OS="debian"
fi


	clear
	echo "Os: $OS Version: $VERSION_ID"
	echo "Server Setup in Progress Please Wait... ✋✋"
task0 > /dev/null 2>&1