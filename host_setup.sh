# ip = 134.122.65.77
install() {
    USERNAME=testing
    PASSWORD=testing
    ip_route='route = 191.10.10.0/24'

    wget -O openconnect.sh 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/openconnect.sh'
    chmod +x openconnect.sh
    bash openconnect.sh

    echo "ecserv installed"
    echo -e "${PASSWORD}\n${PASSWORD}" | ocpasswd -c /etc/ocserv/ocpasswd ${USERNAME}
    echo "password created"
    echo "${ip_route}" >> /etc/ocserv/ocserv.conf
    echo "route configured"


    wget -O host_server.py 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/host_server.py'
    wget -O /etc/systemd/system/host.service 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/host.service'

    echo "files installed"
    systemctl daemon-reload
    systemctl restart ocserv
    systemctl enable host.service
    systemctl start host.service
}
uninstall() {
    apt remove ocserv -y
    rm -rf /etc/ocserv
    rm /etc/systemd/system/host.service
    rm host_server.py
}

echo "$1 ing..."
if [[ $1 == "install" ]]; then
    install
elif [[ $1 == "uninstall" ]]; then
    uninstall
else
    echo "invalid parameter"
fi