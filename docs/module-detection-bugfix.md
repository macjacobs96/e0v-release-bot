# 模块识别 Bug 修复记录

## 问题

用户在群里发：
```
@E0V发版机器人 健康检测：
SA8397_E0V_dev_MST分支
MR：http://10.138.227.87/.../merge_requests/343
Domain Build：http://10.138.227.91:8080/.../AIOS_MST_Domain/46/
```

机器人错误识别为 **SDK** 而非 **健康检测**。

## 原因

旧版 `_detect_module()` 直接搜索全文（含 URL），URL 中的 `Domain`/`Domain_Jobs` 关键词触发了 SDK 匹配，而健康检测在检测顺序中排在 SDK 之后。

## 修复

改为两阶段检测：

1. **Phase 1 — Prefix 匹配**（高优先级）：先用 `re.sub(r'https?://\S+', '', text)` 去掉所有 URL，只看「人写的文字」
2. **Phase 2 — Full text 匹配**（低优先级）：prefix 无结果时才回退到全文

健康检测必须排在 SDK 前面，「Domain Build」是健康检测常见的链接格式。

```python
def _detect_module(self, text):
    prefix = re.sub(r'https?://\S+', '', text).lower()
    t = text.lower()
    
    # Phase 1: explicit labels (strongest)
    if any(kw in prefix for kw in ['健康检测', '健康', 'health', '体检']):
        return 'health'
    if any(kw in prefix for kw in ['sdk', '域控', '域控制器']):
        return 'sdk'
    if any(kw in prefix for kw in ['apk', '客户端', '安卓', 'app包']):
        return 'apk'
    
    # Phase 2: fallback to full text
    ...
```

## 验证

修复后同样输入正确识别为 `health` 模块。
