# Open English Dictionary

一个开源的英英+英汉词典数据集。

该仓库存储的是数据集的原始文件（`NDJSON` 分片），如需直接使用数据库、MDict（mdx）等格式，请访问 [Releases](https://github.com/ImSingee/open-english-dictionary/releases) 页面。

## 当前数据规模

目前数据集中包括约 26w 单词及 2.5w 短语。

目前的数据规模已经足够 99% 的日常场景所使用。该项目背后有一个持续运行的数据 pipeline，会抓取互联网上知名英文媒体的每日更新并加入数据集。当前正在以日 1w+ 的数量级进行扩充，预计会在总数据规模达到 50w 以后进入较低频更新的状态。

## 与其它 AI 词典的区别

1. 持续更新 —— 该 AI 词典会持续更新，快速将新词纳入数据集
2. 更高质量的数据 —— 所有词条均使用最新 SOTA AI 模型生成
3. 结构化的数据 —— 所有词条均使用结构化数据格式存储，可以轻松被程序解析应用于各类场景；同时提供了 sqlite 数据库和 MDict（mdx）词典格式，方便各类工具和应用开箱即用

## 人工反馈

对于任何缺失或不准确的词条，都可以直接通过 [Issue](https://github.com/ImSingee/open-english-dictionary/issues/new) 反馈，会有 Agent 自动处理。

## 协议

MIT