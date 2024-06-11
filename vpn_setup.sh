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

    wget -O openconnect.sh 'https://www.dropbox.com/scl/fi/0p93uiqlu58u5v8z3ckll/openconnect.sh?rlkey=sc3ceh2gyw51xa64ggay1n8zt&st=oseg1gwp&dl=1'
    chmod +x openconnect.sh
    bash openconnect.sh

    echo "ecserv installed"
    echo -e "${PASSWORD}\n${PASSWORD}" | ocpasswd -c /etc/ocserv/ocpasswd ${USERNAME}
    echo "password created"

    wget -O vpn_server.py 'https://www.dropbox.com/scl/fi/qd77mmgy6pav9maw88vdq/vpn_server.py?rlkey=5uy0idjajmmfj8z3hxftlj1mn&st=0vw0qvgw&dl=1'
    wget -O /etc/systemd/system/vpn.service 'https://www.dropbox.com/scl/fi/2zmq95pglkcxjnldfwv8c/vpn.service?rlkey=oopzs4u61nd2dsw36r2t6v2kv&st=si2ag6a9&dl=1'

    apt install openconnect -y
    local oc_file="/etc/systemd/system/openconnect.service"
    wget -O $oc_file 'https://www.dropbox.com/scl/fi/m8lv9aj2vh22277otxf7m/openconnect.service?rlkey=85amq1frsggm7r6vkdqzd0sla&st=f9fmht16&dl=1'

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

