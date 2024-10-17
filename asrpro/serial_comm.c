#include "asr.h"
extern "C"{ void * __dso_handle = 0 ;}
#include "setup.h"
#include "HardwareSerial.h"

uint32_t snid;
void ASR_CODE();

//{speak:思思-知性女声,vol:10,speed:10,platform:haohaodada}
//{playid:10001,voice:欢迎使用语音助手，用草莓熊唤醒我。}
//{playid:10002,voice:我退下了，用熊熊唤醒我}

/*描述该功能...
*/
void ASR_CODE(){
  //本函数是语音识别成功钩子程序
  //运行时间越短越好，复杂控制启动新线程运行
  //唤醒时间设置必须在ASR_CODE中才有效
  set_state_enter_wakeup(10000);
  switch (snid) {
   case 3:
    Serial.println("move");
    break;
   case 4:
    Serial.println("stop");
    break;
   default:
    break;
  }
  //用switch分支选择，根据不同的识别成功的ID执行相应动作，点击switch左上齿轮
  //可以增加分支项
  //除了switch分支选择，也可用如果判断识别ID的值来执行动作
  //采用如果判断模块，可更方便复制

}

void hardware_init(){
  //需要操作系统启动后初始化的内容
  //音量范围1-7
  vol_set(5);
  vTaskDelete(NULL);
}

void setup()
{
  //需要操作系统启动前初始化的内容
  //播报音下拉菜单可以选择，合成音量是指TTS生成文件的音量
  //欢迎词指开机提示音，可以为空
  //退出语音是指休眠时提示音，可以为空
  //休眠后用唤醒词唤醒后才能执行命令，唤醒词最多5个。回复语可以空。ID范围为0-9999
  //{ID:0,keyword:"唤醒词",ASR:"草莓熊",ASRTO:"我在"}
  //{ID:5,keyword:"唤醒词",ASR:"熊熊",ASRTO:"我在"}
  //{ID:1,keyword:"命令词",ASR:"打开灯光",ASRTO:"好的，马上打开灯光"}
  //{ID:2,keyword:"命令词",ASR:"关闭灯光",ASRTO:"好的，马上关闭灯光"}
  //{ID:3,keyword:"命令词",ASR:"动起来",ASRTO:"好的，动一动"}
  //{ID:4,keyword:"命令词",ASR:"停下",ASRTO:"好的，停了"}
  setPinFun(2,FIRST_FUNCTION);
  setPinFun(3,FIRST_FUNCTION);
  setPinFun(5,FIRST_FUNCTION);
  setPinFun(4,FIRST_FUNCTION);
  setPinFun(13,SECOND_FUNCTION);
  setPinFun(14,SECOND_FUNCTION);
  Serial.begin(9600);
}
