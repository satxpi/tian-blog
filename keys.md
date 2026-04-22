# API Keys 汇总

**⚠️ 敏感文件，请勿分享或上传到公开仓库！**

---

## 大模型 API

### 阿里云百炼 (qwen)
- **用途**: 主用模型
- **Key**: `sk-ad7b90eb92ee4a21a9bd02e368b6d9e2`
- **地址**: https://dashscope.aliyuncs.com/compatible-mode/v1

### 智谱 GLM (glm)
- **用途**: 备选模型
- **Key**: `8bccfeadaeb64b15ad1ade9b41bc7805.1gvpELJlPju9LAcI`
- **地址**: https://open.bigmodel.cn/api/paas/v4

### DeepSeek
- **用途**: 推理模型
- **Key**: `sk-146cba82ddee4d2c93bda9cf43025f58`
- **地址**: https://api.deepseek.com/v1

### SiliconFlow (本地/便宜模型)
- **用途**: 快速测试
- **Key**: `sk-pwbtvgsrtyblakeidpbuaanbwdvjtmhbnkoevlduypgovydy`
- **地址**: https://api.siliconflow.cn/v1

### Moonshot (kimi)
- **用途**: 长文本
- **Key**: `sk-146cba82ddee4d2c93bda9cf43025f58` (和 DeepSeek 一样？)
- **地址**: https://api.moonshot.cn/v1

### 腾讯云代码助手
- **用途**: 代码补全
- **Key**: `sk-sp-bxKdO9lATdXgPdirtAvPq6KPxxiwxZpYbhflQBjrLrCjFFnQ`
- **地址**: https://api.lkeap.cloud.tencent.com/coding/v3

---

## 搜索 API

### Tavily (AI 搜索)
- **Key**: `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`
- **位置**: `~/.openclaw/workspace/.env.tavily`

---

## 平台 Secret

### 腾讯云企业微信
- **corpId**: `ww9c4e8a8e9c2b1234`
- **corpSecret**: `XXXXXXXYZabcdegikmoqsvy147ADGKOS` (需要确认)

---

## 使用方式

```bash
# 临时使用某个 key
export OPENAI_API_KEY="sk-xxxxx"

# Tavily
source ~/.openclaw/workspace/.env.tavily

# 在代码中引用
# 配置文件: ~/.openclaw/openclaw.json
```

---

*最后更新: 2026-03-18*
*存储位置: memory/infra.md 或 ~/.openclaw/keys.md*
