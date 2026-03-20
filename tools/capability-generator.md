# 能力描述生成器

Agent能力需要遵循JSON Schema格式定义输入输出。本工具帮助你用自然语言生成标准的能力描述。

## 在线工具

访问: http://localhost:3000/tools/capability-generator

## 使用方法

### 方式1: 可视化表单

1. 打开能力生成器页面
2. 用自然语言描述你的能力，例如：
   - "查询航班需要出发城市、目的地城市、出发日期"
   - "天气查询需要城市名称"
3. 点击"生成"按钮
4. 获取标准JSON Schema

### 方式2: API调用

```bash
curl -X POST http://localhost:8000/api/tools/generate-schema \
  -H "Content-Type: application/json" \
  -d '{
    "description": "查询航班需要出发城市、目的地城市、出发日期",
    "language": "zh"
  }'
```

响应：
```json
{
  "schema": {
    "type": "object",
    "properties": {
      "from_city": {
        "type": "string",
        "description": "出发城市"
      },
      "to_city": {
        "type": "string", 
        "description": "目的地城市"
      },
      "date": {
        "type": "string",
        "description": "出发日期",
        "format": "date"
      }
    },
    "required": ["from_city", "to_city", "date"]
  }
}
```

### 方式3: 本地CLI

```bash
python tools/capability_generator.py "查询航班需要出发城市、目的地城市、出发日期"
```

## 示例

### 航班查询

输入: "查询航班需要出发城市、目的地城市、出发日期，可选舱位等级"

输出:
```json
{
  "name": "flight_search",
  "description": "查询航班信息",
  "input_schema": {
    "type": "object",
    "properties": {
      "from_city": {
        "type": "string",
        "description": "出发城市，如：北京、上海"
      },
      "to_city": {
        "type": "string",
        "description": "目的地城市，如：广州、深圳"
      },
      "date": {
        "type": "string",
        "description": "出发日期，格式：YYYY-MM-DD",
        "format": "date"
      },
      "cabin_class": {
        "type": "string",
        "description": "舱位等级：economy/business/first",
        "enum": ["economy", "business", "first"]
      }
    },
    "required": ["from_city", "to_city", "date"]
  }
}
```

### 天气查询

输入: "查询天气需要城市名称，可选预报天数"

输出:
```json
{
  "name": "weather_query",
  "description": "查询天气信息",
  "input_schema": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "城市名称"
      },
      "days": {
        "type": "integer",
        "description": "预报天数",
        "minimum": 1,
        "maximum": 7,
        "default": 1
      }
    },
    "required": ["city"]
  }
}
```

### 翻译服务

输入: "翻译需要源语言、目标语言、待翻译文本"

输出:
```json
{
  "name": "translate",
  "description": "翻译文本",
  "input_schema": {
    "type": "object",
    "properties": {
      "source_lang": {
        "type": "string",
        "description": "源语言代码，如：en、zh、ja"
      },
      "target_lang": {
        "type": "string",
        "description": "目标语言代码"
      },
      "text": {
        "type": "string",
        "description": "待翻译文本"
      }
    },
    "required": ["source_lang", "target_lang", "text"]
  }
}
```

## 字段类型映射

| 自然语言 | JSON Schema类型 |
|---------|---------------|
| 是/否 | boolean |
| 数字/数量 | integer/number |
| 文本/名称/描述 | string |
| 日期 | string (format: date) |
| 时间 | string (format: time) |
| 列表 | array |
| 对象 | object |

## 注意事项

1. **必填字段**: 用"需要"、"必须"描述的字段会自动标记为required
2. **可选字段**: 用"可选"、"可以不填"描述的字段不会标记为required
3. **枚举值**: 用"只能是"、"包括"描述的字段会生成enum限制
4. **格式验证**: 日期、时间、邮箱、URL等会自动添加format验证
