
rho scan --username $1 --hosts $2 --allow-agent --output pack-scan.csv --report-format date.date,uname.hostname,redhat-release.release,redhat-packages.is_redhat,redhat-packages.num_rh_packages,redhat-packages.num_installed_packages,redhat-packages.last_installed,redhat-packages.last_built,virt-what.type,virt.virt,virt.num_guests,virt.num_running_guests,cpu.count,cpu.socket_count

