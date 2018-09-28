
# Pi Ducky Server

## Description

Connect a Raspberry Pi zero W to another computer.
The Pi will act as a keyboard that you'll be able to control remotely using [Ducky Scripts](https://www.hak5.org/gear/duck/ducky-script-usb-rubber-ducky-101).

The Pi will broadcast its own hidden (if so desired) Wifi network, so you'll be able to connect to it remotely, and interactively run
keyboard commands on the connected computer.

Basically, a remote penetration testing tool for $10, assuming you alreay have an SD card and a micro USB to USB A cable.


## DISCLAIMER

Use this tool at your own risk.

Please don't use it to do anything stupid or illegal. The purpose of the project is automation and learning. Not harming others.


## Installation and Setup

Start by going over [this great guide](https://randomnerdtutorials.com/raspberry-pi-zero-usb-keyboard-hid/) to turn your Pi into a software defined keyboard.

We only need to do steps 1-3. Here's a quick recap of the commands:

```bash
$ echo "dtoverlay=dwc2" | sudo tee -a /boot/config.txt
$ echo "dwc2" | sudo tee -a /etc/modules
$ sudo echo "libcomposite" | sudo tee -a /etc/modules

$ sudo touch /usr/bin/kbsetup
$ sudo chmod +x /usr/bin/kbsetup
```

edit `/etc/rc.local`, adding the following line before `exit 0`:

    /usr/bin/kbsetup > /var/tmp/kbsetup.log 2>&1


Now let's create the configuration for our HID device by editing `/usr/bin/kbsetup`:

```bash
#!/bin/bash
cd /sys/kernel/config/usb_gadget/
mkdir -p isticktoit
cd isticktoit
echo 0x046d > idVendor # Logitech, Inc.
echo 0xc24d > idProduct # G710 Gaming Keyboard
echo 0x0100 > bcdDevice # v1.0.0
echo 0x0200 > bcdUSB # USB2
mkdir -p strings/0x409
echo "Logitech, Inc." > strings/0x409/manufacturer
echo "G710 Gaming Keyboard" > strings/0x409/product
mkdir -p configs/c.1/strings/0x409
echo "Config 1: ECM network" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# Add functions here
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol
echo 1 > functions/hid.usb0/subclass
echo 8 > functions/hid.usb0/report_length
echo -ne \\x05\\x01\\x09\\x06\\xa1\\x01\\x05\\x07\\x19\\xe0\\x29\\xe7\\x15\\x00\\x25\\x01\\x75\\x01\\x95\\x08\\x81\\x02\\x95\\x01\\x75\\x08\\x81\\x03\\x95\\x05\\x75\\x01\\x05\\x08\\x19\\x01\\x29\\x05\\x91\\x02\\x95\\x01\\x75\\x03\\x91\\x03\\x95\\x06\\x75\\x08\\x15\\x00\\x25\\x65\\x05\\x07\\x19\\x00\\x29\\x65\\x81\\x00\\xc0 > functions/hid.usb0/report_desc
ln -s functions/hid.usb0 configs/c.1/
# End functions

ls /sys/class/udc > UDC
```

I've taken the keyboard vendor and product IDs from http://www.linux-usb.org/usb.ids - but you can leave them as is.
Once done, reboot your Pi. There should be a file named `/dev/hidg0` in your system.

If there isn't one, check the log at `/var/tmp/kbsetup.log` for info.


## Install the code

```bash
$ sudo apt-get install git python3-pip
$ sudo mkdir -p /opt/ducky-server && sudo chown pi:pi /opt/ducky-server

$ git clone https://github.com/ozkatz/pi-remote-ducky.git /opt/ducky-server
$ cd /opt/ducky-server && sudo python3 -m pip install -r requirements.txt
```

Let's also create another directory to keep our custom Ducky scripts in:

```bash
$ sudo mkdir -p /opt/ducky-scripts && sudo chown pi:pi /opt/ducky-scripts
```

## Setup the server

```bash
$ sudo ln -s /opt/ducky-server/ducky-server.service /etc/systemd/system/
$ sudo systemctl daemon-reload
$ sudo systemctl enable ducky-server
$ sudo systemctl start ducky-server
```

## Connecting to the Pi - Setting up a hidden Wifi network

Basically, [follow this guide](https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md).
Here's a recap:

```bash
$ sudo apt-get install dnsmasq hostapd
$ sudo systemctl stop dnsmasq
$ sudo systemctl stop hostapd
```

Edit `/etc/dhcpcd.conf`, pasting in the following:

    interface wlan0
        static ip_address=192.168.4.1/24
        nohook wpa_supplicant

Edit `/etc/dnsmasq.conf`, pasting in the following:

    interface=wlan0      # Use the require wireless interface - usually wlan0
      dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h

And `/etc/hostapd/hostapd.conf`, with the following content:

    interface=wlan0
    driver=nl80211
    ssid=mywifinet
    hw_mode=g
    channel=7
    wmm_enabled=0
    macaddr_acl=0
    auth_algs=1
    ignore_broadcast_ssid=0
    wpa=2
    wpa_passphrase=evilraspberry
    wpa_key_mgmt=WPA-PSK
    wpa_pairwise=TKIP
    rsn_pairwise=CCMP

Feel free to rename the Wifi network to something else, and of course, change its password.

Lastly, edit `/etc/default/hostapd`:

    DAEMON_CONF="/etc/hostapd/hostapd.conf"

Finally, reboot your Pi (or simply connect it using the micro USB connection to the host computer).
Be sure to use the USB port labeled "USB" and not the one labeled "PWR". Wait a couple of minutes and try to connect to the new Wifi network we created.

Once connected, direct your browser at [http://192.168.4.1:5000/](http://192.168.4.1:5000/).
