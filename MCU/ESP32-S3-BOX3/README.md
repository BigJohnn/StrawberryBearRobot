这个模块主要用于实现以下功能：

语音唤醒，在线语音识别，chatgpt对话，在线语音合成，屏幕显示，喇叭输出

屏幕模块最终会成为机器人的脸，它被设计为用来传达机器人情感，以及在合适的时候显示一些信息如温湿度。

***
### 说明

1.由于openai的访问限制，使用百度千帆LLM做了相应替换；

2.按照 https://github.com/espressif/esp-box/tree/master/examples/chatgpt_demo 将项目环境搭建好后，会出现**managed_components**文件夹；

3.将**OpenAI.c**替换同名文件，注意，需要以下步骤：

	a.申请自己的语音识别、语音合成服务，并创建相应应用，获取相应ACCESS_KEY,并替换{YOUR_ACCESS_TOKEN_A_NO_{}} x2

	b.申请自己的千帆大模型服务，并创建相应应用，获取相应ACCESS_KEY,{YOUR_ACCESS_TOKEN_NO_B_{}} x1

	c.注意代码中cuid改成自己的，如MAC地址，详情见百度相关api说明文档

***
**TODOs**:

1.与MPU的通信，by WIFI.

2.温湿度检测;

3.NLP（意图识别、实体抽取）;