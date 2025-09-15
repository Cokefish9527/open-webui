# 测试脚本说明文档

本文档说明了[test](file:///c:/work/open-webui/test)目录下各个测试脚本的用途和版本信息。

## 完整测试脚本

### 1. [comprehensive_hsai_test.py](file:///c:/work/open-webui/test/comprehensive_hsai_test.py)
- **用途**: 综合HSAI事件处理器测试脚本
- **功能**: 全面测试HSAI系统的各项功能，包括WebSocket连接、认证、消息发送和响应监听
- **特点**: 
  - 测试HSAI聊天消息和工作流触发消息
  - 包含完整的测试流程和结果验证
  - 适用于日常的综合功能测试

### 2. [final_connection_test.py](file:///c:/work/open-web-webui/test/final_connection_test.py)
- **用途**: 最终版WebSocket连接测试脚本
- **功能**: 测试WebSocket连接和认证功能
- **特点**: 
  - 修复了路径和参数问题
  - 是连接测试的最终版本
  - 适用于快速验证WebSocket连接功能

### 3. [final_websocket_n8n_test.py](file:///c:/work/open-webui/test/final_websocket_n8n_test.py)
- **用途**: 最终版WebSocket与n8n集成测试脚本
- **功能**: 完整测试WebSocket与n8n工作流的集成
- **特点**: 
  - 解决了HTTP 403错误问题
  - 包含完整的测试流程，从连接建立到工作流触发和响应接收
  - 适用于验证WebSocket与n8n的完整集成

## 使用建议

- 对于日常测试，请根据需要选择合适的测试脚本：
  - 如果需要快速验证WebSocket连接，使用[final_connection_test.py](file:///c:/work/open-webui/test/final_connection_test.py)
  - 如果需要测试HSAI系统的完整功能，使用[comprehensive_hsai_test.py](file:///c:/work/open-webui/test/comprehensive_hsai_test.py)
  - 如果需要测试WebSocket与n8n的集成，使用[final_websocket_n8n_test.py](file:///c:/work/open-webui/test/final_websocket_n8n_test.py)

- 所有脚本都包含了详细的日志输出，便于调试和问题排查
- 在维护测试脚本时，请基于现有脚本进行修改，不要创建新的中间验证脚本
