# Agent Workflow

1. 用户发送消息。
2. 后端读取短期会话和用户画像。
3. `RouterAgent` 判断是否属于业务范围。
4. `RequirementAgent` 补全目标平台、类目和预算。
5. `ProductConsultantAgent` 输出初步选品建议。
6. 后端保存用户消息、执行过程和 final 消息。
7. `MemoryService` 维护最近 10 轮短期记忆；每 10 轮压缩一次进入长期记忆。
8. `UserProfileAgent` 在管理端“生成长期记忆”时读取用户记忆和最近会话，输出画像更新计划，再由后端写入 `UserProfile` 和 `UserMemory`。
9. `RecallAgent` 在“一键召回”中读取用户画像、记忆和 `TrendingItem` 爆品库，生成候选评分、召回理由和召回文案。
