//以下代码只在上电时运行一次,一般用于全局变量定义和上电初始化数据
int sys0=0,sys1=0,sys2=0     //全局变量定义目前仅支持4字节有符号整形(int),不支持其他类型的全局变量声明,如需使用字符串类型可以在页面中使用变量控件来实现
int pintai,pentou
int lang=0,zoffset_step=1,open_filament_step=10,babystep_step=1,printing_filament_step=10,move_step=1,filament_step=10,manual_level_step=1,auto_level_step=2
int sleep_counts=0
int kbmode=1,kbmin=8
int sleep_time=300
int max_dim=100
int min_dim=0
int print_page=0
bauds=115200
lang=0
dims=100
repo lang,100
if(lang<0||lang>12)
{
  lang=2
}
repo sleep_time,200
if(sleep_time!=0&&sleep_time!=300&&sleep_time!=900&&sleep_time!=1800)
{
  sleep_time=300
}
page ${page:logo}   //上电刷新第0页
