# restore-file-extension
还原文件的扩展名

## 环境
python3.6+

## 使用方法
在 settings.json 中配置好扩展名与文件开头**十六进制数**的对应，
随后在脚本所在的文件夹中打开终端，执行：
```
python restore_ext.py {<目标文件路径>|-r <目标文件夹路径>}
```
