# Flutter Mobile（规划中）

Mobile 端通过同一 Runtime API 通信。

## 推荐结构

```text
mobile/
├── lib/
│   ├── main.dart
│   ├── api/brain_api.dart    # 对应 shared/types.ts
│   ├── screens/
│   │   ├── dashboard.dart
│   │   ├── chat.dart
│   │   └── models.dart
│   └── providers/            # Riverpod
```

## API Base URL

开发环境默认 `http://10.0.2.2:8000`（Android 模拟器访问宿主机）。

```dart
// lib/api/brain_api.dart
final baseUrl = 'http://10.0.2.2:8000';
```

初始化 Flutter 项目：

```bash
flutter create --org com.brainmemory mobile_app
```
