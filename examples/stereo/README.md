# Open-XiaoAI Stereo

不同型号的小爱音箱组立体声。

## 功能

- 在小爱音箱上独立运行，无需服务端部署
- 支持不同型号的小爱音箱局域网组立体声
- 支持蓝牙播放和小爱音箱自带的音乐播放
- 支持局域网内主从设备服务发现自动连接
- 支持主从节点“热拔插”，自动切换声道
- 支持前向纠错(FEC)和丢包补偿(PLC)

## 快速开始

> [!NOTE]
> 以下操作需要先将小爱音箱刷机， 然后 SSH 连接到小爱音箱。👉 [教程](../../docs/flash.md)

首先，分别在两台设备上配置主从和声道。

```shell
# 首先确保配置文件路径存在
mkdir -p /data/open-xiaoai || true

# 如果你想让左边的小爱音箱作为主音源
echo master left > /data/open-xiaoai/stereo.conf # 在左边的小爱音箱上执行
echo slave right > /data/open-xiaoai/stereo.conf # 在右边的小爱音箱上执行

# 如果你想让右边的小爱音箱作为主音源
# echo master right > /data/open-xiaoai/stereo.conf # 在右边的小爱音箱上执行
# echo slave left > /data/open-xiaoai/stereo.conf # 在左边的小爱音箱上执行
```

配置完成后，分别在两台设备上运行下面的启动脚本即可。

```shell
curl -sSfL https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-stereo/init.sh | sh
```

如果你想要开机自启动，运行以下命令重启小爱音箱即可（需要先按上面的步骤配置主从设备和声道）。

```shell
# 下载 boot.sh 到 /data/init.sh 开机时自启动
curl -L -o /data/init.sh https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-stereo/boot.sh

# 重启小爱音箱
reboot
```

## 注意事项

- 不支持同步音量大小（不同型号设备的音量基准不同，请手动调整）
- 不支持多路音频混音（同时播放多个音频听起来像是信号故障、静音卡顿）
- 目前只支持小爱音箱 Pro（LX06）和小米智能音箱 Pro（OH2P）这两个机型（需要刷机）
- 从设备会主动同步主设备的音源，反之不支持（建议禁用从设备的麦克风和操作，防止音频叠加）

## License

MIT License © 2024-PRESENT [Del Wang](https://del.wang)
