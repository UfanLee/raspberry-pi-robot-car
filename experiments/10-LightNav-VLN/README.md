# Task 10 — 树莓派小车的 LightNav-0 视觉语言导航

```text
树莓派（相机、测距、电机） ↔ 本机 Ubuntu / WSL（两条 SSH 隧道） ↔ GPU 云主机（LightNav-0）
```

树莓派把前视 JPEG 和指令经 Ubuntu 发给模型，从返回的第一个局部路点选取直行、原地转向或停车。动作结束后停车并重新拍照。客户端复用实验 09 的 PiCamera、超声波和 LOBOROBOT 驱动，PWM 沿用 30。 [LightNav-0 官方协议](https://github.com/lightorigins/LightNav-0/blob/main/docs/PROTOCOL.md)

## 云端

在 GPU 主机启动模型并等待服务显示 `READY`：

```bash
PORT=8050 lightnav-serve --task vln --model_path /path/to/LightNav-0 --backend vllm_local
```

## 本机 Ubuntu / WSL

在 Ubuntu 终端用云实例提供的 SSH 用户、地址和端口建立正向隧道，保持此终端运行：

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -L 127.0.0.1:8050:127.0.0.1:8050 -p SSH_PORT GPU_USER@GPU_HOST
```

在另一个 Ubuntu 终端反向转发并登录树莓派。第二条命令在树莓派的回环地址上建立入口，连接经由 Ubuntu 转到云端服务：

```bash
ssh -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -R 127.0.0.1:8050:127.0.0.1:8050 PI_USER@PI_HOST
```

## 树莓派

使用实验 09 已配置的 Python 3.8+ 环境。退出 FPV 程序，保留实验 09 和 10 的目录结构，从树莓派上的仓库根目录执行：

```bash
python -m pip install -r experiments/10-LightNav-VLN/requirements.txt
python experiments/10-LightNav-VLN/task10_vln_pi.py --drive \
  --server ws://127.0.0.1:8050 \
  --instruction "Go to the blue chair in front of you and stop."
```

使用 `--duration 60 --steps 120` 将单轮导航限制在约 60 秒，或按 Ctrl+C 提前停车。每次动作前，树莓派要求超声波距离有效且大于 15 cm。连接失败或模型返回停车时，本次运行结束。单次电机指令约 120 ms。

## 纯视觉连续控制

用 `--vision-only --duration 60` 替代 `--drive`。此模式按视觉路点控制车轮，等待下一条决策时保持当前动作，若连续 2 秒没有更新则先停轮。带前进分量的转向路点走向前弧线。模型停车信号、运行时间到达或连接错误都会停车。

## 记录 VLN 演示

在树莓派运行纯视觉命令时追加 `--record ~/lightnav-pi/demos/blue-jar-01`。记录目录应是新目录，保存发给云端的原始 JPEG 和 `events.jsonl`。日志按序号记录指令、往返时间、模型原始响应，以及纯视觉模式实际下发的轮命令。模型的停车信号可以从日志核对；实车是否停在目标前仍需对照现场录像或停车后的画面。

## 目标起初不在画面内

在离线布置场地时把药罐放在初始视野之外、转动车头后可见的位置。运行 `--vision-only --search --duration 60 --record ~/lightnav-pi/demos/blue-jar-search-01`，使用目标描述指令。模型输出 `visible=false` 时，车优先执行模型的移动路点。若模型没有给出移动，则短暂左转获取新视角。看到目标后继续跟随模型路点，只有目标可见时才把模型的 `stop=true` 作为到达停车。

每条运动指令有独立的短时限，平移时限随第一路点的前向分量缩短。实车没有里程反馈，距离和转角仍需实测。演示日志应能对照初始帧、首次看见目标的帧、接近帧和停车响应。

## 连续采集与运动（固定云台）

在纯视觉命令中加 `--smooth`，可与 `--search` 同用。PiCamera 持续取帧，客户端只把最新帧交给空闲的推理请求。控制器用前几个方向一致的路点估算有限行程，等待新路点时执行剩余行程。首个前进路点小于 10 cm 时只使用这一点，收到停车指令或用完行程就停止。默认以 `--speed-mps 0.28` 估算行程，这是初始值，需按实际地面和 PWM 30 下的速度校准。

加 `--record` 可核对每帧的时间和每次下发的 `motion_budget_s`。云台目前保持居中。这一模式连续读取相机，可视化仍使用已保存的推理帧。
