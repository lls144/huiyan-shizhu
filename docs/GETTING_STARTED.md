# 运行与复现

[首页](../README.md) · [文档索引](INDEX.md)

## 电脑上的离线入口

已在 Windows / Python 3.12 验证。虚拟环境安装根目录 `requirements.txt` 后：

```powershell
python -m pc.gui --source synthetic
python -m simulator --scenario all
python -m pytest -q pc/tests tests plc/tests
```

`synthetic` 是明确的合成输入；Fake PLC 不连接真实控制器。相机采集、图像处理、事件和通信层的测试分开放在 `pc/tests`、`tests` 与 `plc/tests`。

## USB 相机

```powershell
python -m pc.camera --config pc/config/camera.json enumerate
python -m pc.gui --source camera --camera-config pc/config/camera.json --roi-mode auto
```

先根据枚举结果修改相机配置，再摆放背景与物料、校准 ROI。现存真实验收包含 Insta360 与内置 HD Webcam 两套条件，不保证任意曝光、焦距、角度和遮挡条件下都能复现相同结果。

## 真机 PLC

1. 安装额外依赖：`python -m pip install -r plc/tools/requirements.txt`（python-snap7 3.1.2）。
2. 按 [TIA V20 编译指南](../plc/project/TIA_V20_COMPILE_GUIDE.md) 导入 SCL，核对 CPU、I/O、DB 布局与访问设置。
3. 根据现场修改 [PLC 配置](../pc/config/plc.json)。公开版本中的 TEST-NET 地址用于说明，不是实际设备地址。
4. 阅读 [硬件验证记录](../plc/docs/PLC_HARDWARE_VERIFICATION.md)，再运行 `python -m pc.sorting --source camera`。

真实 PLC 工具会写入命令或改变输出；不要把它们当作纯只读健康检查。具体参数以各工具 `--help` 为准。仓库保留 SCL 和重建步骤，没有附带整个 TIA 安装环境或设备许可证。
