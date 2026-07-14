# Prompt 组装与压缩模板

## 何时读取

核心观点、现实场景、主体动作、构图、光线和色调均已确定，需要写最终正向 Prompt 时
读取。本文件只负责组装与压缩，不补充新的观点、主体或视觉策略。

## 长度契约

- 中文正向 Prompt：`50–60` 个汉字。
- 英文正向 Prompt：`35–45` 个英文单词。
- Negative Prompt 独立输出，不计入正向 Prompt 长度。
- Midjourney 比例参数仅在明确需要时追加，参数不计入英文正文词数。
- 长度不足时补充会改变画面的具体信息；长度超出时按下方顺序压缩。

## 必留信息

按重要性从高到低：

1. 真实摄影或可信现实影像；
2. 一个主体；
3. 一个具体地点；
4. 一个可观察动作；
5. 一个能证明核心关系的状态或物件；
6. 可解释光线；
7. 适配色调；
8. 封面必要留白，或正文必要的空间关系。

## 场景化压缩顺序

超出长度预算时，从后向前处理：

1. 删除分辨率、镜头品牌、“高级感”“电影感”等无决策价值词。
2. 删除分析原因、文章结论和 Negative Prompt 中才需要的禁止项。
3. 合并同义风格词，例如“温暖、柔和、自然”压为“暖色自然”。
4. 删除不影响主关系的背景装饰、辅助人物和第二种材质。
5. 把界面细节压成一个可见状态，把流程压成一个关键转换动作。
6. 把多个动作压成最能证明观点的一个动作。
7. 最后才缩短地点、主体和核心关系；不得先删掉现实场景。

压缩后重新检查：是否仍能回答“什么主体、在哪里、发生什么变化、什么关系可见、什么光线”。

## 中文模型

适用于 GPT Image、Seedream 及中文回退模型：

```text
真实摄影，【主体】在【具体地点】【一个动作】，
【证明核心关系的状态或物件】，【自然或现场光线】，【色调】，【必要空间】。
```

封面示例，中文 `51` 个汉字：

```text
真实摄影，运维人员在数据中心调度台分配等待任务，有限计算槽位仍有队列，冷静中性色，侧面工作光，左侧低纹理留白区域。
```

正文示例，中文 `50` 个汉字：

```text
真实摄影，医生在阅片室核对系统提示与原始影像，手指停在待确认区域，柔和中性光，低饱和蓝灰，背景简洁，保留工作痕迹。
```

## 英文模型

适用于 Midjourney、Flux、Ideogram：

```text
Realistic editorial photography, [subject] in [specific place],
[one visible action], [one state or object proving the relationship],
[explainable light], [color mood], [required spatial treatment].
```

封面示例，英文 `38` 词：

```text
Realistic editorial photography, an operator at a data-center console assigning queued jobs to limited compute slots, several tasks still waiting, neutral industrial colors, controlled side lighting, restrained equipment detail, clean low-texture space on the left for a headline.
```

正文示例，英文 `36` 词：

```text
Realistic documentary photography, a doctor in a radiology room comparing one system alert with the original scan before confirming it, soft neutral task lighting, muted blue-gray colors, readable hand movement, uncluttered background, no dramatic medical effects.
```

## 按子策略组装

### 现实场景

```text
摄影方式 + 人物或实物 + 真实地点 + 人的动作或物体状态变化 + 结果状态 + 光线 + 色调
```

### 桌面演示

```text
真实桌面摄影 + 少量实体物件 + 一个分配、流动或转换状态 + 必要时出现手部 + 自然光线 + 清晰空间
```

### 真实 UI

```text
真实设备 + 一个已确认界面状态 + 一次反馈、操作或核对 + 必要时出现人物 + 现场光线 + 低噪音背景
```

### 流程

```text
真实工作台或桌面 + 同一工件 + 三到四个顺序状态 + 一个关键转换点 + 均匀清晰光线
```

### 同主体对照

```text
同一主体与固定视角 + 两个相邻状态 + 只改变一个变量 + 一致光线与背景
```

这些都是正文配图模式内的写法，不构成新的输出模式。

## 禁止把分析塞入 Prompt

不要写：

```text
这张图表达平台竞争从模型能力转向生态控制，并提醒读者注意长期风险……
```

应改为可见场景：

```text
采购者在统一接入台把有限席位移向符合规则的工具，其他申请仍在等待。
```

## 最终检查

- 是否只有一个主体、一个动作和一个核心关系？
- 是否包含明确主体、地点、人的动作或物体状态变化，以及光线？
- 是否删除机器人、Logo、代码雨、随机 HUD 等替代观点的元素？
- 封面是否保留可用标题空间，正文是否优先解释关系？
- 中文是否为 50–60 个汉字，英文是否为 35–45 个单词？
