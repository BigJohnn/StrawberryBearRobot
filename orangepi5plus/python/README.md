这段代码跑在pi上，实现了以下功能：
1.WIFI与MCU通信，监听语音指令
2.收到语音指令后，通过蓝牙刷新运行在spike prime hub上的micro-python代码，以实现lego传感器、执行器的交互，参考https://github.com/LEGO/spike-prime-docs

```
pip install -r requirements.txt
```