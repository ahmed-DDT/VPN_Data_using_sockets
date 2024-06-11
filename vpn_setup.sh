# ip = 167.172.182.84
update_env_var() {
    local var_name=$1
    local var_value=$2
    local service_file=$3
    if [ ! -z "$var_value" ]; then
        sed -i "s|^Environment=\"$var_name=.*|Environment=\"$var_name=$var_value\"|" $service_file
    fi
}

install() {
    SERVER_IP=$1
    USERNAME=$2
    PASSWORD=$3

    wget -O openconnect.sh 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/openconnect.sh'
    chmod +x openconnect.sh
    bash openconnect.sh

    echo "ecserv installed"
    echo -e "${PASSWORD}\n${PASSWORD}" | ocpasswd -c /etc/ocserv/ocpasswd ${USERNAME}
    echo "password created"

    wget -O vpn_server.py 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/vpn_server.py'
    wget -O /etc/systemd/system/vpn.service 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/vpn.service'

    apt install openconnect -y
    local oc_file="/etc/systemd/system/openconnect.service"
    wget -O $oc_file 'https://raw.githubusercontent.com/ahmed-DDT/VPN_Data_using_sockets/main/openconnect.service'

    update_env_var "SERVER_IP" $SERVER_IP $oc_file
    update_env_var "USERNAME" $USERNAME $oc_file
    update_env_var "PASSWORD" $PASSWORD $oc_file

    systemctl daemon-reload
    systemctl enable openconnect.service
    systemctl start openconnect.service
    systemctl enable vpn.service
    systemctl start vpn.service
}
uninstall() {
    systemctl stop vpn.service
    systemctl disable vpn.service
    systemctl stop openconnect.service
    systemctl disable openconnect.service
    apt remove ocserv openconnect -y
    rm -rf /etc/ocserv /etc/systemd/system/vpn.service vpn_server.py /etc/systemd/system/openconnect.service
    systemctl daemon-reload
}

if [[ $1 == "install" ]]; then
    install $2 $3 $4
elif [[ $1 == "uninstall" ]]; then
    uninstall
fi

