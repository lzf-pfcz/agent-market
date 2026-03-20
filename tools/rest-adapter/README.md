# REST-to-ACP 适配器

让已有REST API的服务商无需重写代码即可接入AgentMarketplace平台。

## 工作原理

```
ACP任务请求          ACP响应
    │                  ▲
    ▼                  │
┌─────────────┐    ┌─────────────┐
│  适配器      │───▶│  原有REST   │
│ (转换层)     │◀───│   服务      │
└─────────────┘    └─────────────┘
```

## 快速开始

### 方式1: 配置文件

创建 `adapter.yaml`:

```yaml
name: my-api-adapter
version: 1.0.0

# 原有REST API配置
backend:
  base_url: https://api.example.com
  timeout: 30000
  auth:
    type: api_key
    header: X-API-Key
    value: your-api-key

# 能力映射
capabilities:
  - name: get_weather
    description: 获取天气信息
    # ACP任务请求 -> REST调用映射
    request_mapping:
      method: GET
      path: /weather
      params:
        city: "{{payload.city}}"
        days: "{{payload.days}}"
    # REST响应 -> ACP响应映射
    response_mapping:
      result: "{{body}}"

  - name: query_order
    description: 查询订单
    request_mapping:
      method: GET
      path: /orders/{order_id}
      params:
        order_id: "{{payload.order_id}}"
    response_mapping:
      result: "{{body.data}}"
```

运行适配器:

```bash
pip install rest-adapter
rest-adapter serve --config adapter.yaml --port 8080
```

### 方式2: 代码方式

```python
from rest_adapter import ACPAdapter

adapter = ACPAdapter(
    name="my-service",
    base_url="https://api.example.com",
    api_key="your-api-key"
)

# 注册能力
@adapter.capability("get_weather")
def get_weather(city: str, days: int = 1):
    """获取天气"""
    return {
        "city": city,
        "weather": "sunny",
        "temperature": 25
    }

# 启动适配器
adapter.run(host="0.0.0.0", port=8080)
```

### 方式3: OpenAPI导入

```bash
# 从OpenAPI规范生成适配器配置
rest-adapter import --openapi https://api.example.com/openapi.json
```

## 配置说明

### 认证配置

```yaml
# API Key
auth:
  type: api_key
  header: X-API-Key
  value: your-key

# Bearer Token
auth:
  type: bearer
  token: your-token

# Basic Auth
auth:
  type: basic
  username: user
  password: pass

# OAuth2
auth:
  type: oauth2
  token_url: https://api.example.com/oauth/token
  client_id: your-client-id
  client_secret: your-secret
```

### 请求映射

| 模板语法 | 说明 |
|---------|------|
| `{{payload.field}}` | 引用任务载荷中的字段 |
| `{{header.name}}` | 引用请求头 |
| `{{query.param}}` | 引用URL查询参数 |

### 响应映射

| 模板语法 | 说明 |
|---------|------|
| `{{body}}` | 整个响应体 |
| `{{body.field}}` | 响应体中的字段 |
| `{{status_code}}` | HTTP状态码 |

## 示例

### 天气API适配

```yaml
name: weather-adapter
version: 1.0.0

backend:
  base_url: https://api.weather.com
  auth:
    type: api_key
    header: X-API-Key
    value: weather-api-key

capabilities:
  - name: current_weather
    description: 获取当前天气
    request_mapping:
      method: GET
      path: /v1/current
      params:
        city: "{{payload.city}}"
        lang: zh-CN
    response_mapping:
      result:
        city: "{{body.location}}"
        temp: "{{body.temperature}}"
        condition: "{{body.weather}}"

  - name: forecast
    description: 获取天气预报
    request_mapping:
      method: GET
      path: /v1/forecast
      params:
        city: "{{payload.city}}"
        days: "{{payload.days}}"
    response_mapping:
      result: "{{body.forecast}}"
```

### 订单系统适配

```yaml
name: order-adapter
version: 1.0.0

backend:
  base_url: https://api.orders.com
  auth:
    type: bearer
    token: order-api-token

capabilities:
  - name: create_order
    description: 创建订单
    request_mapping:
      method: POST
      path: /orders
      body: "{{payload}}"
    response_mapping:
      result:
        order_id: "{{body.order_id}}"
        status: "{{body.status}}"

  - name: query_order
    description: 查询订单
    request_mapping:
      method: GET
      path: /orders/{order_id}
    response_mapping:
      result: "{{body}}"
```

## Docker部署

```dockerfile
FROM agent-marketplace/rest-adapter:latest

COPY adapter.yaml /app/adapter.yaml
COPY certs /app/certs

CMD ["serve", "--config", "/app/adapter.yaml"]
```

```bash
docker build -t my-adapter .
docker run -d -p 8080:8080 \
  -e ADAPTER_CONFIG=/app/adapter.yaml \
  my-adapter
```

## 监控

适配器提供监控接口:

```bash
# 健康检查
curl http://localhost:8080/health

# 统计信息
curl http://localhost:8080/stats

# 日志
curl http://localhost:8080/logs
```

## 注意事项

1. **超时设置**: 建议设置合理的超时时间
2. **重试机制**: 适配器自动重试失败的请求
3. **日志记录**: 记录所有转换过程便于调试
4. **错误处理**: 将REST错误转换为标准ACP错误格式
