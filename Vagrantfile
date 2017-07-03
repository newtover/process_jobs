# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-16.04-i386"
  config.vm.network "forwarded_port", guest: 5000, host: 5000, host_ip: "127.0.0.1"

  # Work around disconnected virtual network cable.
  config.vm.provider "VirtualBox" do |vb|
    vb.customize ["modifyvm", :id, "--cableconnected1", "on"]
  end

  config.vm.provision "shell", inline: <<-SHELL
    # this fixes a bug in grub-pc: https://bugs.launchpad.net/ubuntu/+source/grub2/+bug/1258597
    # sed -ie 's/^GRUB_HIDDEN/#GRUB_HIDDEN/' /etc/default/grub
    apt-get -qqy update
    # https://github.com/mitchellh/vagrant/issues/289
    DEBIAN_FRONTEND=noninteractive apt-get -qqy upgrade
    #apt-get -qqy install make zip unzip 

    apt-get -qqy install python3-pip
    pip3 install --upgrade pip
    pip3 install -r /vagrant/requirements.txt

    vagrantTip="[35m[1mThe shared directory is located at /vagrant\\nTo access your shared files: cd /vagrant[m"
    echo -e $vagrantTip > /etc/motd

    echo "Done installing your virtual machine!"
  SHELL
end
