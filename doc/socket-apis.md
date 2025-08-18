# OpenRA Copilot Socket APIs

本接口文档描述了 OpenRA 中 AI Copilot 使用的各类指令及参数格式。  

OpenRA在一局游戏进入世界后，会用**socket**，监听**7445**端口**TCP**协议，**UTF-8** **json**格式的报文

# **整体报文Json结构**

### *请求报文结构：**

```
{
  "apiVersion": "1.0",
  "requestId": "uuid-string",
  "command": "command_name",
  "params": {
    // 命令参数
  },
  "language": "zh"
} 
```

| **参数名** | **类型** | **必需** | **说明**                                             |
| ---------- | -------- | -------- | ---------------------------------------------------- |
| apiVersion | string   | 是       | API版本号，固定为"1.0"，用于校验是否和服务器版本匹配 |
| requestId  | string   | 是       | 请求唯一标识符，和响应包对应，传啥都行               |
| command    | string   | 是       | 命令名称，用于区分命令                               |
| params     | object   | 否       | 命令参数                                             |
| language   | string   | 否       | 语言设置，可选值：zh/en，默认zh                      |

### **响应报文结构：**

#### 成功响应:

```
{
  "status": 1,
  "requestId": "uuid-string",
  "response": "成功消息",
  "data": {
    // 返回数据
  }
}
```

#### 错误响应:

```
{
  "status": -1,
  "requestId": "uuid-string",
  "error": {
    "code": "ERROR_CODE",
    "message": "错误消息",
    "details": {
      // 错误详情
    }
  }
}
```

ERROR_CODE详细内容见附录1

# **数据结构**

###  **方向（direction）**

#### str

后文中出现所有方向相关的str，都使用的下方的候选字段，方向后也可在后缀加上“方/侧/边"或者不加，同样有效

```
case "北":
case "上": return new CVec(0, -1);  
 
case "右上":
case "东北": return new CVec(1, -1);  
 
case "东":
case "右": return new CVec(1, 0); 
 
case "右下":
case "东南": return new CVec(1, 1);  
 
case "南":
case "下": return new CVec(0, 1);  
 
case "左下":
case "西南": return new CVec(-1, 1);  
 
case "西":
case "左": return new CVec(-1, 0);  
 
case "左上":
case "西北": return new CVec(-1, -1); 
 
case "任意":
case "左右":
case "上下":
case "附近":
case "旁": return GetRandomDirection(); 
```

 

### 通用Target结构（targets）

目标筛选结构用于定义一组单位的选择规则，该结构体旨在通过条件，获取到符合条件的Actor列表，所有Actor必须满足在己方视野中，可在多数指令中使用：

Sample：

```
{
  "actorId": [1, 2, 3],
  "range": "screen",
  "groupId": [2, 3],
  "type": ["士兵", "炮兵"],
  "faction": "己方",
  "restrain": [
    {
      "relativeDirection": "左下",
      "maxNum": 2
    }
  ]
}
```

​                ● actorId（可选，int）：指定唯一单位 ID 列表，填写后将忽略其他筛选条件，actorId可通过某些指令查询获得。

​                ● range（可选，str）：目标范围，支持：all（默认）、screen、selected。分别表示，全部，屏幕中单位，选中单位中

​                ● groupId（可选，int）：约束目标所属组 ID 列表。

​                ● type（可选，str）：单位中文名称，支持多个类型，内部将转为配置名匹配，具体type列表见附录2。

​                ● faction（可选，str）：阵营筛选，支持：己方、敌方、中立。

​                ● restrain（可选）：进一步约束筛选结果，所有约束条件会从前到后依次执行，每个条件可能对Actor列表产生一定的修改。

​                ○ relativeDirection（str）：优先选择指定方向上的单位，仅会对列表排序，支持八方向，指定方向上的单位会被排序在前面

​                ○ maxNum（int）：保留Actor列表中前maxNum个单位。

​                ○ distance（int）：相对于 location 的曼哈顿距离限制，会剔除距离以外的单位。  

### **位置（location）**

表示一个目标位置，可用于指令参数：

Sample1:

```
{
  "x": 12,
  "y": 6
}
```

Sample:2

```
{
  "targets": { ... },
  "direction": "上",
  "distance": 5
}
```

有两种方式表示一个坐标，一个是直接给 (x,y) ，另一种是用一个单位和相对偏移，会检测是否同时提供了 x, y 字段，来决定是否使用绝对坐标。

​                ● x,y（int）：位置的直接坐标

​                ● targets：用于计算平均位置的单位选择包。

​                ● direction（str）：基于平均位置的相对方向，支持八方向

​                ● distance（int）：偏移距离，单位为格子。

若同时提供 x, y 字段，则视为绝对坐标。

# **命令性指令**

不同指令通过不同的"command": "command_name"，来区分

下文中不同指令的包，指的是请求包中的  "params": {  }部分

###  

### **move_actor - 移动单位**

**Command**：move_actor

**Sample Params**：



```
{
  "targets": {
    "range": "selected"
  },
  "direction": "东北",
  "distance": 6,
  "isAttackMove": 1
}
```

**描述**： 移动指定的游戏单位到目标位置，或沿指定方向进行偏移，可指定为攻击或强制突击移动。

**参数**：

​                ● targets（object，必填）：目标单位选择器，见通用Target结构。

​                ● location（object，可选）：目标位置，如 {"x": 10, "y": 20}。

​                ● direction（string，可选）：方向关键字，支持："东","西","南","北","东北","东南","西北","西南"。

​                ● distance（int，可选）：向指定方向移动的距离，正整数。

​                ● path（array，可选）：完整路径点数组，如 [{"x": 1, "y": 2}, ...]。

​                ● isAttackMove（int，可选）：是否为攻击移动，1 表示启用，0 为普通移动，默认 0。

​                ● isAssaultMove（int，可选）：是否为强制突击移动，1 表示启用，默认 0。

 

### **attack - 攻击目标**

**Command**：attack

**Sample Params**：



```
{
  "attackers": {
    "range": "selected"
  },
  "targets": {
    "type": ["敌方建筑"]
  }
}
```

**描述**： 命令攻击者攻击指定目标。

**参数**：

​                ● attackers（object，必填）：攻击单位选择器，见通用Target结构。

​                ● targets（object，必填）：攻击目标单位选择器，见通用Target结构。

 

### **select_unit - 选择单位**

**Command**：select_unit

**Sample Params**：



```
{
  "targets": {
    "type": ["士兵"],
    "faction": "己方"
  },
  "isCombine": 0
}
```



**描述**： 选择指定的游戏单位。

**参数**：

​                ● targets（object，必填）：目标单位选择器。

​                ● isCombine（int，可选）：是否与当前选择合并，1 表示合并，0 表示替换，默认 0。

 

### **form_group - 编组单位**

**Command**：form_group

**Sample Params**：



```
{
  "targets": {
    "range": "selected"
  },
  "groupId": 3
}
```

**描述**： 将选中的单位编入指定编队。

**参数**：

​                ● targets（object，必填）：目标单位选择器。

​                ● groupId（int，必填）：编队ID，建议在 1-10 范围内。

 

### **camera_move - 移动镜头**

**Command**：camera_move

**Sample Params**：



```
{
  "direction": "西南",
  "distance": 8
}
```

**描述**： 移动游戏视角到指定位置或方向。

**参数**：

​                ● location（object，可选）：跳转到的地图坐标位置，如 {"x": 15, "y": 30}。

​                ● direction（string，可选）：移动方向，支持："东","西","南","北","东北","东南","西北","西南"。

​                ● distance（int，可选）：向指定方向移动的格子数，正整数。

 

### **deploy - 部署单位**

**Command**：deploy

**Sample Params**：



```
{
  "targets": {
    "type": ["基地车"]
  }
}
```

**描述**： 部署选中的单位（目前只有基地车可以部署）。

**参数**：

​                ● targets（object，必填）：单位筛选结构。

 

### **stop - 停止单位**

**Command**：stop

**Sample Params**：



```
{
  "targets": {
    "range": "selected"
  }
}
```

**描述**： 停止选中单位的当前行动。

**参数**：

​                ● targets（object，必填）：单位筛选结构。

 

### **repair - 修理单位/建筑**

**Command**：repair

**Sample Params**：

```
{
  "targets": {
    "type": ["电厂"]
  }
}
```





**描述**： 修理选中的单位或建筑。

**参数**：

​                ● targets（object，必填）：单位或建筑的筛选结构。

 

### **view - 查看单位**

**Command**：view

**Sample Params**：

```
{
  "actorId": 123
}
```

**描述**： 将镜头移动到指定单位位置。

**参数**：

​                ● actorId（int，必填）：目标单位 ID。



### **set_rally_point - 设置集结点**

**Command**：set_rally_point

**Sample Params**：



```
{
  "targets": {
    "type": ["兵营"]
  },
  "location": {
    "x": 10,
    "y": 20
  }
}
```

**描述**： 为生产建筑设置集结点。

**参数**：

​                ● targets（object，必填）：可设置集结点的单位。

​                ● location（object，必填）：指定的目标位置。

 

### **place_building - 放置建筑**

**Command**：place_building

**Sample Params**：



```
{
  "queueType": "Building",
  "location": {
    "x": 25,
    "y": 18
  }
}
```

**描述**： 在地图上放置已生产完成的建筑。

**参数**：

​                ● queueType（string，必填）：所属生产队列类型，支持："Building","Defense","Infantry","Vehicle","Aircraft","Naval"。

​                ● location（object，可选）：建筑放置目标坐标。

 

### **manage_production - 管理生产队列**

**Command**：manage_production

**Sample Params**：



```
{
  "queueType": "Vehicle",
  "action": "pause"
}
```





**描述**： 管理指定生产队列，暂停、继续或取消正在排队的生产任务。

**参数**：

​                ● queueType（string，必填）：目标生产队列类型，支持："Building","Defense","Infantry","Vehicle","Aircraft","Naval"

​                ● action（string，必填）：操作类型，支持："pause", "resume", "cancel"。

 

### **start_production - 开始生产**

**Command**：start_production

**Sample Params**：



```
{
  "units": [
    {"unit_type": "电厂", "quantity": 1}
  ],
  "autoPlaceBuilding": false
}
```

**描述**： 请求生产单位或建筑。

**参数**：

​                ● units（array，必填）：生产单位及数量列表。

​                ● autoPlaceBuilding（bool，可选）：若为 true，建筑单位完成后自动放置。

# **查询性指令**

查询指令的响应内容，指的响应包中的"data": {  }部分

### **query_can_produce - 查询可生产单位**

**Command**：query_can_produce

**Sample Params**：

```
{
  "unit_type": "重工厂"
}
```

**描述**： 检查是否能够生产指定单位或建筑。

**参数**：

​                ● unit_type（str，必填）：单位类型

**响应示例**：

```
{
  "can_produce": true,
  "response": ""
}
```

**响应字段说明**：

​                ● can_produce（bool）：是否可以生产。

​                ● response（string）：若can_produce为false的具体原因

 

### **query_production_queue - 查询生产队列**

**Command**：query_production_queue

**Sample Params**：

 



```
{
  "queueType": "Infantry"
}
```

**描述**： 查询指定类型生产队列的当前状态。

**参数**：

​                ● queueType（string，必填）：所属生产队列类型，支持："Building","Defense","Infantry","Vehicle","Aircraft","Naval"。

**响应字段（data）**：

```
{
  "queue_type": "Infantry",
  "queue_items": [
    {
      "name": "infantry",
      "chineseName": "步兵",
      "remaining_time": 3.0,
      "total_time": 5.0,
      "remaining_cost": 100,
      "total_cost": 200,
      "paused": false,
      "done": false,
      "progress_percent": 50,
      "owner_actor_id": 101,
      "status": "in_progress"
    }
  ],
  "has_ready_item": false
}
```

**响应字段说明**：

​                ● queue_type（string）：查询的队列类型。

​                ● queue_items（array）：每个项目的生产状态：

​                ○ name（string）：配置名称。

​                ○ chineseName（string）：中文名称。

​                ○ remaining_time（float）：剩余时间。

​                ○ total_time（float）：总时间。

​                ○ remaining_cost（int）：剩余花费。

​                ○ total_cost（int）：总花费。

​                ○ paused（bool）：是否暂停。

​                ○ done（bool）：是否已完成。

​                ○ progress_percent（int）：当前进度（0~100）。

​                ○ owner_actor_id（int）：所属建筑的ID。

​                ○ status（string）：状态（completed / paused / in_progress / waiting）。

​                ● has_ready_item（bool）：是否有已完成的项目。

 

### **query_wait_info - 查询等待状态**

**Command**：query_wait_info

**Sample Params**：

```
{
  "waitId": 1002
}
```

**描述**： 查询由start_production指令返回的 waitId 是否已完成。

**参数：**

​                ● waitId（必填，int）

**响应字段（data）**：

```
{
  "waitStatus": "completed"
}
```

**响应字段说明****：**

​                ● waitStatus（string）：状态枚举（如：completed、in_progress、invalid）。

 

### **query_path - 查询路径**

**Command**：query_path

**Sample Params**：



```
{
  "targets": {
    ...
  },
  "destination": {
    "x": 50,
    "y": 20
  },
  "method": "shortest"
}
```

**描述**： 计算单位从当前位置到目标位置的路径信息。

**参数：**

​                ● targets（object，必填）：寻路单位。

​                ● destination（object，必填）：路径终点位置。

​                ● method（string，可选）：寻路算法类型，如 "shortest"（默认）。支持："Left","Right"，也可写作"左路"，"右路"

 

**响应字段（data）**：



```
{
  "path": [
    {"x": 12, "y": 10},
    {"x": 13, "y": 10},
    {"x": 14, "y": 10}
  ]
}
```

**响应字段说明**：

​                ● path（array）：路径点列表，每项包含：

​                ○ x（int）：坐标X。

​                ○ y（int）：坐标Y。

 

### **query_actor - 查询单位信息**

**Command**：query_actor

**Sample Params**：

```
{
  "targets": {
    "range": "selected"
  }
}
```

**描述**： 返回目标单位的详细信息。

**参数：**

​                ● targets（object，必填）：查询单位。

**响应字段（data）**：

```
{
  "actors": [
    {
      "id": 101,
      "type": "步兵",
      "faction": "己方",
      "hp": 100,
      "maxHp": 100,
      "isDead": false,
      "position": {"x": 20, "y": 25}
    }
  ]
}
```

**响应字段说明**：

​                ● actors（array）：单位信息列表：

​                ○ id（int）：单位 ID。

​                ○ type（string）：单位中文名。

​                ○ faction（string）：所属阵营（己方/敌方/中立）。

​                ○ hp（int）：当前生命。

​                ○ maxHp（int）：最大生命。

​                ○ isDead（bool）：是否死亡。

​                ○ position.x / position.y（int）：地图坐标。

 

### **player_baseinfo_query - 查询玩家基地信息**

**Command**：player_baseinfo_query

**Sample Params**：

```
{}
```

**描述**：

查询玩家当前的金钱、电力、人口等基础资源信息。

**参数**：无。

**响应示例**（data）：

```
{
  "Cash": 3000,
  "Resources": 120,
  "Power": 25,
  "PowerDrained": 15,
  "PowerProvided": 40
}
```

**响应字段说明**：

​                ● Cash（int）：玩家当前金钱。

​                ● Resources（int）：资源数量。 （注：Cash+Resource为玩家实际金钱）

​                ● Power（int）：剩余电力。

​                ● PowerDrained（int）：已用电量。

​                ● PowerProvided（int）：总供电。

 

### **screen_info_query - 查询屏幕信息**

**Command**：screen_info_query

**Sample Params**：

```
{}
```

**描述**：

返回当前屏幕边界、鼠标状态和地图坐标。

**参数**：无。

**响应示例**（data）：

```
{
  "ScreenMin": {"X": 10, "Y": 20},
  "ScreenMax": {"X": 40, "Y": 50},
  "IsMouseOnScreen": true,
  "MousePosition": {"X": 30, "Y": 35}
}
```

**响应字段说明**：

​                ● ScreenMin.X / Y（int）：屏幕左上角地图坐标。

​                ● ScreenMax.X / Y（int）：屏幕右下角地图坐标。

​                ● IsMouseOnScreen（bool）：鼠标是否在屏幕显示区域内。

​                ● MousePosition.X / Y（int）：鼠标当前指向的地图坐标。

 

### **map_query - 查询地图信息**

**Command**：map_query

**Sample Params**：

```
{}
```

**描述**：

返回地图整体结构、大小、可见性与资源布局。

**参数**：无。

**响应示例**（data）：

```
{
  "MapWidth": 3,
  "MapHeight": 3,
  "Height": [[0,1,1],[0,1,1],[0,0,0]],
  "IsVisible": [[true,true,false],[true,false,false],[false,false,false]],
  "IsExplored": [[true,true,true],[true,true,true],[false,false,false]],
  "Terrain": [["dirt","dirt","rock"],["dirt","grass","grass"],["rock","rock","rock"]],
  "ResourcesType": [["ore","ore","none"],["ore","none","none"],["none","none","none"]],
  "Resources": [[2,3,0],[1,0,0],[0,0,0]]
}
```

**响应字段说明**：

​                ● MapWidth / MapHeight（int）：地图宽度和高度。

​                ● Height（二维int数组）：每格的高度。

​                ● IsVisible（二维bool数组）：是否当前可见。

​                ● IsExplored（二维bool数组）：是否已被探索。

​                ● Terrain（二维string数组）：地形类型（如 dirt、rock 等）。

​                ● ResourcesType（二维string数组）：资源类型（如 ore、none）。

​                ● Resources（二维int数组）：资源强度值。

 

### **fog_query - 查询战争迷雾**

**Command**：fog_query

**Sample Params**：

```
{
  "pos": {"x": 8, "y": 14}
}
```

**描述**：

判断某地图位置是否被战争迷雾遮挡。**参数**：

​                ● pos（object，必填）：地图位置坐标。

**响应示例**（data）：

```
{
  "IsVisible": false,
  "IsExplored": true
}
```

**响应字段说明**：

​                ● IsVisible（bool）：当前位置是否可见。

​                ● IsExplored（bool）：当前位置是否已被探索。

 

### **unit_attribute_query - 查询单位属性**

**Command**：unit_attribute_query

**Sample Params**：

```
{
  "targets": {"range": "selected"}
}
```

**描述**：

返回单位属性，包括速度、攻击能力与可攻击目标。**参数**：

​                ● targets（object，必填）：单位筛选结构。

**响应示例**（data）：

```
{
  "attributes": [
    {
      "id": 1234,
      "type": "步兵",
      "speed": 90,
      "hasAttackRange": true,
      "targets": [5678]
    }
  ]
}
```

**响应字段说明**：

​                ● attributes（array）：单位属性列表：

​                ○ id（int）：单位 ID。

​                ○ type（string）：中文单位类型。

​                ○ speed（float）：移动速度。

​                ○ hasAttackRange（bool）：是否具备攻击能力。

​                ○ targets（array of int）：扫描到的可攻击目标 ID 列表。

 

### **ping - 心跳检测**

**Command**：ping

**Sample Params**：

```
{}
```

**描述**：

检测服务器状态与返回当前版本时间戳。**参数**：无。

**响应示例**（data）：

```
{
  "timestamp": "2025-06-27 21:35:12"
}
```

**响应字段说明**：

​                ● timestamp（string）：服务器当前时间戳（格式 yyyy-MM-dd HH:mm:ss）。

 

# **附录**

## **附录1 错误代码说明**

| **错误代码**                 | **中文描述**               | **英文描述**                              |
| ---------------------------- | -------------------------- | ----------------------------------------- |
| INVALID_REQUEST              | 无效的JSON格式             | Invalid JSON format                       |
| INVALID_VERSION              | 不支持的API版本            | Unsupported API version                   |
| COMMAND_EXECUTION_ERROR      | 命令执行失败               | Command execution failed                  |
| QUERY_EXECUTION_ERROR        | 查询执行失败               | Query execution failed                    |
| INVALID_COMMAND              | 未知的命令                 | Unknown command                           |
| INTERNAL_ERROR               | 服务器内部错误             | Server internal error                     |
| INVALID_PARAMS_MOVE_ACTOR    | 移动命令参数不能为空       | Move command parameters cannot be empty   |
| MISSING_TARGETS              | 缺少targets参数            | Missing targets parameter                 |
| INVALID_PARAMS_ATTACK        | 攻击命令参数不能为空       | Attack command parameters cannot be empty |
| MISSING_ATTACKERS_OR_TARGETS | 缺少attackers或targets参数 | Missing attackers or targets parameter    |

## **附录****2 单位类型名称对照**

附录2主要由两部分构成，单位名称和单位集合昵称

 

单位名称部分结构为：

配置名:若干个别名

在上述API中，使用配置名或者别名都是可以的

集合昵称为若干单位的集合，也可以在上述API中使用，意指集合中所有类型

  powr:

​        发电厂

​        电厂

​        小电

​        小电厂

​        基础电厂

​        power plant

​        basic power plant

​        pp

​        pwr

​        power

​    barr:

​        兵营

​        兵工厂

​        苏军兵营

​        红军兵营

​        soviet barracks

​        soviet inf

​        red barracks

​    proc:

​        矿场

​        采矿场

​        矿

​        精炼厂

​        矿石精炼厂

​        ore refinery

​        ref

​        refinery

​        ore ref

​    weap:

​        战车工厂

​        车间

​        坦克厂

​        坦克工厂

​        载具工厂

​        war factory

​        wf

​        factory

​    dome:

​        雷达站

​        雷达

​        侦察站

​        雷达圆顶

​        radar dome

​        radar station

​        rad

​        dome

​    fix:

​        维修厂

​        修理厂

​        维修站

​        修理站

​        service depot

​        repair bay

​        rep

​        repair

​        serv

​    apwr:

​        核电站

​        核电厂

​        大电

​        大电厂

​        高级电厂

​        advanced power plant

​        nuclear reactor

​        nuke power

​        np

​        adv power

​    afld:

​        空军基地

​        机场

​        飞机场

​        航空站

​        airfield

​        airbase

​        air

​        af

​    stek:

​        科技中心

​        高科技

​        高科技中心

​        研究中心

​        实验室

​        tech center

​        research facility

​        tech

​        lab

​    ftur:

​        火焰塔

​        喷火塔

​        喷火碉堡

​        防御塔

​        flame tower

​        flame turret

​        ft

​        flame def

​    tsla:

​        特斯拉塔

​        电塔

​        特斯拉线圈

​        高级防御塔

​        tesla coil

​        tesla tower

​        tc

​        tes

​    sam:

​        防空导弹

​        防空塔

​        防空炮

​        防空炮塔

​        防空

​        山姆飞弹

​        sam site

​        surface-to-air missile

​        aa

​        anti air

​    e1:

​        步兵

​        枪兵

​        步枪兵

​        普通步兵

​        rifle infantry

​        basic infantry

​        rifle

​        rifleman

​    e3:

​        火箭兵

​        火箭筒兵

​        炮兵

​        火箭筒

​        导弹兵

​        rocket soldier

​        rocket infantry

​        rocket

​        rl

​    harv:

​        采矿车

​        矿车

​        矿物收集车

​        ore collector

​        harvester

​        miner

​        harv

​        collector

​    apc:

​        装甲运输车

​        装甲车

​        运兵车

​        armored personnel carrier

​        troop transport

​        transport

​        carrier

​    ftrk:

​        防空车

​        防空炮车

​        移动防空车

​        flak truck

​        mobile anti-air

​        flak

​        aa truck

​    mcv:

​        基地车

​        建造车

​        移动建设车

​        mcv

​        mobile construction vehicle

​        builder

​        constructor

​    3tnk:

​        重型坦克

​        重坦

​        犀牛坦克

​        犀牛

​        heavy tank

​        rhino tank

​        ht

​        rhino

​    4tnk:

​        超重型坦克

​        猛犸坦克

​        猛犸

​        天启坦克

​        天启

​        mammoth tank

​        super heavy tank

​        mam

​        mammoth

​        mt

   fact:

​        建造厂

​        基地

​        主基地

​        主要建筑

​        construction yard

​        main base

​        cy

​        con yard

​        base

​    yak:

​        雅克战机

​        雅克

​        雅克攻击机

​        苏联战机

​        yak fighter

​        soviet fighter

​        yakattack

​        ya

​    mig:

​        米格战机

​        米格

​        米格战斗机

​        mig fighter

​        soviet interceptor

​        mig29

​        mg

 

nickname:

​    士兵: 表示所有士兵

​    载具: 表示所有载具

​    坦克: 表示所有坦克

​    战斗单位: 表示所有除了采矿车和基地车以外的单位

​    建筑: 所有建筑