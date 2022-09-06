---
layout: post
title: "Adding power related targets to systemd"
---

systemd has a bunch of nice "power" related targets that come shipped by
default. For example, `sleep.target` is extremely useful if you want to lock
your screen on sleep.

One thing which systemd doesn't have, at least yet, is targets which relate to
going on to and coming back off of AC and battery power. This is pretty easy to
do, though, and provides the convenience of sleep.target for events like this.
I want to use these to do some power tweaks when coming on to and off of
battery.

First off, create the two targets that you want to use for AC/battery:

    cat > /etc/systemd/system/ac.target << 'EOF'
    [Unit]
    Description=On AC power
    DefaultDependencies=no
    StopWhenUnneeded=yes
    EOF

<!-- -->

    cat > /etc/systemd/system/battery.target << 'EOF'
    [Unit]
    Description=On battery power
    DefaultDependencies=no
    StopWhenUnneeded=yes
    EOF

A systemd "target" is essentially a systemd unit that is used to perform
actions when a certain state is reached in the system. We'll be using these as
the binding points for services that we want to run when we switch to and from
AC/battery.

Now, we need to tell udev to start `ac.target` when it sees us coming on to
AC, and start `battery.target` when it sees us coming off of AC. To find the
events we need to attach to, we can use `udevadm monitor --environment`:

    # udevadm monitor --environment
    UDEV  [7041.262327] change   /devices/.../power_supply/AC (power_supply)
    [...]
    POWER_SUPPLY_ONLINE=0

You can also use `udevadm info -a -p /sys/class/power_supply/AC` to tie this
information to the relevant keys in udev:

    % udevadm info -a -p /sys/class/power_supply/AC

    looking at device '/devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A08:00/device:19/PNP0C09:00/ACPI0003:00/power_supply/AC':
       KERNEL=="AC"
       SUBSYSTEM=="power_supply"
       DRIVER==""
       ATTR{SUBSYSTEM}=="power_supply"
       ATTR{POWER_SUPPLY_NAME}=="AC"
       ATTR{POWER_SUPPLY_ONLINE}=="1"

Based on this, we can see that we need to attach our target startup to the
`power_supply` object, on the `online` attribute. All we have to do now is to
tell udev to do this by creating a rules file:

    cat > /etc/udev/rules.d/99-powertargets.rules << 'EOF'
    SUBSYSTEM=="power_supply", KERNEL=="AC", ATTR{online}=="0", RUN+="/usr/sbin/systemctl start battery.target"
    SUBSYSTEM=="power_supply", KERNEL=="AC", ATTR{online}=="1", RUN+="/usr/sbin/systemctl start ac.target"
    EOF

We can now reload and apply udev's new config:

    # udevadm control --reload-rules

We can now test it out by unplugging the power and seeing what happens:

    % sudo systemctl status battery.target
    ● battery.target - On battery power
       Loaded: loaded (/etc/systemd/system/battery.target; static; vendor preset: disabled)
       Active: inactive (dead)

    Oct 29 12:24:33 roujiamo systemd[1]: Reached target On battery power.
    Oct 29 12:24:33 roujiamo systemd[1]: battery.target: Unit not needed anymore. Stopping.
    Oct 29 12:24:33 roujiamo systemd[1]: Stopped target On battery power.

Sweet, it works! Now that everything is setup, we can add the services that we
want to start based on these targets. Take this as an example, and note the
`[Install]` section. You need to enable the service, as well, or the symlinks
to `battery.target.wants` won't be created.

    % systemctl cat powerdown.service
    # /etc/systemd/system/powerdown.service
    [Unit]
    Description=Laptop battery savings

    [Service]
    Type=oneshot
    ExecStart=/usr/local/bin/powerdown

    [Install]
    WantedBy=battery.target

Try unplugging again after enabling the service, and you should see it working,
too:

    % sudo systemctl status powerdown
    ● powerdown.service - Laptop battery savings
       Loaded: loaded (/etc/systemd/system/powerdown.service; enabled; vendor preset: disabled)
       Active: inactive (dead) since Sun 2017-10-29 02:24:33 GMT; 22min ago
      Process: 15977 ExecStart=/usr/local/bin/powerdown (code=exited, status=0/SUCCESS)
     Main PID: 15977 (code=exited, status=0/SUCCESS)

    Oct 29 12:24:33 roujiamo systemd[1]: Starting Laptop battery savings...
    Oct 29 12:24:33 roujiamo systemd[1]: Started Laptop battery savings.

Plug it back in, and you should also see the same for whatever you have
attached to `ac.target`.
