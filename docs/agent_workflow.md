# Agent Workflow

1. 用户发送消息。
2. 后端读取短期会话和用户画像。
3. `RouterAgent` 判断是否属于业务范围。
4. `RequirementAgent` 补全目标平台、类目和预算。
5. `ProductConsultantAgent` 输出初步选品建议。
6. 后端保存用户消息、trace 消息和 final 消息。
7. `UserProfileAgent` 从对话中提取标签并更新画像权重。
