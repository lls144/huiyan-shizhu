# 最终交付物骨架

本目录只放**结构**：章节骨架、分镜、用例矩阵。真实数据、截图和结论一律从证据链引用，不在本目录复制或编造。

## 文件

| 文件 | 对应 Requirement | 状态 |
|---|---|---|
| [REPORT_OUTLINE.md](REPORT_OUTLINE.md) | DELIV-001 综合实验报告（≥4000 字） | 骨架，待真机数据填充 |
| [TEST_CASE_MATRIX.md](TEST_CASE_MATRIX.md) | DELIV-005 测试报告、TEST-001 多工况 | 模板，结果列全部待填 |
| [PPT_OUTLINE.md](PPT_OUTLINE.md) | DELIV-006 答辩 PPT（10 分钟） | 骨架，待彩排 |
| [VIDEO_STORYBOARD.md](VIDEO_STORYBOARD.md) | DELIV-007 演示视频（2–3 分钟） | 分镜，待真机录制 |

## 统一填写规则

1. 每个数字、图片、结论必须能定位到 `notes/tests/`、`evidence/` 或 `plc/records/` 中的真实记录。
2. 尚无真实证据的位置写 `TODO` 或“待测试”，不得先填结论再补实验。
3. 区分证据类型：`离线软件` / `合成输入` / `真实摄像头` / `Fake PLC 模拟` / `TIA 编译` / `真实 PLC`。不同类型不得互相替代。
4. 引用一个具体版本：报告、PPT、视频与 `git commit` 必须一致。
5. 目前可用的真实证据只到 M1–M6，见 [REPORT_EVIDENCE.md](../REPORT_EVIDENCE.md)。
