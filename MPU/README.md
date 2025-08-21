注意, 如果你用的是x86台式机,以下内容可以忽略,因为nomachine自带的nxserver支持开机自启,足矣!
----------------------------------------------------------------------------------

最初使用香橙派5PLUS，但是手头的香橙派没有配散热，导致slam跑起来经常飙到80+摄氏度；

改为风扇散热的树莓派4b，运行稳定且功耗低，20000mAh充电宝不开slam工作2小时约掉电6%

树莓派4b设置headless运行，并连接nomachine远程桌面的方法：

1.添加一个系统服务
```
sudo vim /etc/systemd/system/load_virtual_desktop.service
```
```
[Unit]
Description=Stop GDM and start NX Server
After=network.target

[Service]
Type=simple
ExecStart=/bin/sh -c "sudo systemctl stop gdm; sudo /etc/NX/nxserver --restart"

[Install]
WantedBy=multi-user.target
```
2.启动这个服务
```
sudo systemctl daemon-reload
sudo systemctl start load_virtual_desktop
sudo systemctl enable load_virtual_desktop
sudo reboot
```
其工作的原理是，系统启动时先禁用桌面服务gdm，然后重启nxserver，使得nomachine自己创建framebuffer去绘制远程桌面。
