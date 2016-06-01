VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "centos/7"

  # Create the rho-dev box
  config.vm.define "rho-dev" do |dev|
    dev.vm.synced_folder ".", "/vagrant/rho", type: "nfs", nfs_version: 4, nfs_udp: false
    dev.vm.host_name = "rho-dev.example.com"

    dev.ssh.forward_x11 = true

    dev.vm.provider :libvirt do |domain|
        domain.cpus = 1
        domain.graphics_type = "spice"
        domain.memory = 2048
        domain.video_type = "qxl"
    end

    dev.vm.provision "ansible" do |ansible|
        ansible.playbook = "vagrant/rho-dev.yml"
    end
  end

  # Define a different box to be scanned during tests
  config.vm.define "test_1" do |test_1|
        test_1.vm.host_name = "test1.example.com"

        test_1.ssh.forward_x11 = true

        test_1.vm.provider :libvirt do |domain|
            domain.cpus = 1
            domain.graphics_type = "spice"
            domain.memory = 2048
            domain.video_type = "qxl"
        end

        test_1.vm.provision "ansible" do |ansible|
            ansible.playbook = "vagrant/test_1.yml"
        end
    end
end
