# 阶段 4 压力测试结果 — houhei-two-axis-human-nature（h01）

- 测试日期: 2026-08-05
- 方法: **独立 sub-agent 盲测**（1 个干净 judge sub-agent，只给本 skill 的 SKILL.md + 整包 10-skill name/description 列表 + 打乱顺序的用户 prompt；不给 type / expected_behavior / notes / 通过标准）
- 测试集: 9 条（4 should_trigger + 3 should_not_trigger + 2 edge_case）

## 判定结果

| 测试用例 | 类型 | 盲测判断 | 通过 |
|---|---|---|---|
| should-trigger-01（技术主管升不上去） | should_trigger | 激活 h01（厚维强/黑维缺位韩信型） | ✅ |
| should-trigger-02（新产品失败复盘） | should_trigger | 激活 h01（厚→黑→外部三段归因） | ✅ |
| should-trigger-03（合伙人讲情面评估） | should_trigger | 激活 h01（黑维缺位配置评估） | ✅ |
| should-trigger-04（太要面子提离职） | should_trigger | 激活 h01（厚维缺位/受不得气） | ✅ |
| should-not-trigger-01（厚黑概念查询） | should_not_trigger | NO，直接讲解概念 | ✅ |
| should-not-trigger-02（空降总监三把火） | should_not_trigger | OTHER(houhei-power-behavior) | ✅ |
| should-not-trigger-03（教做人狠一点） | should_not_trigger | OTHER(houhei-lens-not-prescription) | ✅ |
| edge-01（被老板骂该不该怼） | edge_case | NO（即时情绪应对，非评估/复盘） | ✅ |
| edge-02（销售总监单情境证据） | edge_case | 激活 h01 但正确提示「证据不足，需多情境交叉」 | ✅ |

## 统计

- should_trigger: **4/4**
- should_not_trigger（诱饵容错 0）: **3/3**
- edge_case: **2/2**
- 总通过率: **9/9 = 100%**

## 失败分析

无失败 case。唯一需要记录的边界：edge-02 盲测正确激活本 skill 并按 B 边界「仅凭单情境不得硬打分」输出证据不足提示，与预期一致。

## 跨 skill 混淆覆盖

- 诱饵 2 → 应激活 **houhei-power-behavior**（h05 权力情境）✅ 盲测命中
- 诱饵 3 → 应激活 **houhei-lens-not-prescription**（h08 元认知）✅ 盲测命中
- 反向诱饵（h01 语言信号「复盘/归因」出现在 h03/h06 的测试集中）在其他 skill 盲测中均被正确拦截，未抢调 h01。

## 结论

**通过，接受**。无需回炉，description 无歧义。

## 下一步

阶段 5（交付）。
