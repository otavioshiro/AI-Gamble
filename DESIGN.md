# 游戏功能增强设计文档

本文档旨在为“互动小说游戏”项目设计两项核心新功能：
1.  **随机化作家与作品**：在每局游戏开始时，根据所选的小说类型，随机生成具有代表性风格的作家名和作品名。
2.  **故事线路图生成与可视化**：在游戏开始前，预先生成整个故事的主线、关键节点和多结局，并将其以 JSON 格式提供给前端进行可视化。

---

## 第一阶段：后端架构重构

### 1. 数据模型扩展 (`app/models/game.py`)

为了存储新的数据，我们需要在 `Game` 模型中添加新字段。

**修改方案:**

在 `Game` class 中添加 `author`, `title` 和 `story_map` 字段。`story_map` 将以 JSON 字符串的形式存储。

```python
# app/models/game.py

class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    story_type: str
    writing_style: Optional[str] = Field(default=None)
    
    # --- 新增字段 ---
    author: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    story_map: Optional[str] = Field(default=None) # Store story map as JSON string
    # --- 结束 ---

    created_at: datetime.datetime = # ...
    # ... a reste of the file
```

### 2. 数据传输模式扩展 (`app/schemas/game.py`)

我们需要更新 API 的响应模型，以便将新的数据（作者、标题、故事线路图）传递给前端。

**修改方案:**

修改 `GameStartResponse`，加入 `author`, `title` 和 `story_map`。

```python
# app/schemas/game.py

class GameStartResponse(BaseModel):
    game_id: int
    scene: Scene
    
    # --- 新增字段 ---
    author: str
    title: str
    story_map: dict # The story map will be a JSON object
    # --- 结束 ---
```

### 3. 核心服务层重构 (`app/services/story_generator.py`)

这是本次重构的核心。我们需要引入一个全新的机制来生成故事大纲。

**修改方案:**

1.  **创建小说风格数据结构**: 在文件顶部定义一个字典，用于存储不同类型小说的代表性作家和书名风格。

    ```python
    # app/services/story_generator.py

    NOVEL_THEMES = {
        "东方玄幻": {
            "authors": ["天蚕土豆", "我吃西红柿", "辰东", "唐家三少"],
            "title_keywords": ["尊", "帝", "神", "诀", "录", "传"]
        },
        "西方魔幻": {
            "authors": ["托尔金", "乔治·马丁", "J.K.罗琳"],
            "title_keywords": ["之戒", "与火之歌", "的考验", "编年史"]
        },
        # ... 其他类型
    }
    ```

2.  **创建新的 `generate_story_map` 函数**: 这个函数将是新功能的核心，它会调用 LLM 生成一个完整的故事结构。

    ```python
    # app/services/story_generator.py

    async def generate_story_map(client: openai.AsyncOpenAI, story_type: str, author: str, title: str) -> dict:
        """
        Generates a complete story map including plot, key nodes, and endings.
        """
        prompt = f"""
        你是一个金牌游戏策划。请为一部名为《{title}》、由'{author}'创作的'{story_type}'风格的互动小说，设计一个完整的故事线路图。
        
        请遵循以下要求：
        1.  **结构**: 必须包含一个开端(start_node)、多个中间节点(middle_nodes)和一个或多个结局(end_nodes)。
        2.  **JSON 格式**: 你的回答必须是严格的 JSON 格式，结构如下：
            {{
              "title": "{title}",
              "author": "{author}",
              "story_map": {{
                "nodes": [
                  {{ "id": "start", "label": "故事开端", "details": "详细描述..." }},
                  {{ "id": "node_1", "label": "关键抉择A", "details": "详细描述..." }},
                  {{ "id": "node_2", "label": "关键抉择B", "details": "详细描述..." }},
                  {{ "id": "end_good", "label": "光明结局", "details": "详细描述..." }},
                  {{ "id": "end_bad", "label": "黑暗结局", "details": "详细描述..." }}
                ],
                "edges": [
                  {{ "from": "start", "to": "node_1", "label": "选择希望" }},
                  {{ "from": "start", "to": "node_2", "label": "选择力量" }},
                  {{ "from": "node_1", "to": "end_good", "label": "坚持信念" }},
                  {{ "from": "node_2", "to": "end_bad", "label": "堕入深渊" }}
                ]
              }}
            }}
        3.  **内容**: 节点描述需简洁且充满悬念，边标签代表玩家的选择。
        
        请现在生成这个JSON对象。
        """
        # ... (LLM call logic)
        # Returns the parsed JSON dictionary
    ```

3.  **修改 `generate_initial_scene`**: 让它调用新的 `generate_story_map` 函数，并从中提取初始场景。

    ```python
    # app/services/story_generator.py

    async def generate_initial_scene(story_type: str) -> dict:
        # 1. Randomly pick author and generate title
        # ... (logic using NOVEL_THEMES)

        # 2. Generate the full story map
        story_map_data = await generate_story_map(client, story_type, author, title)

        # 3. Extract the first scene from the map
        start_node = next(node for node in story_map_data['story_map']['nodes'] if node['id'] == 'start')
        initial_choices = [
            {"id": i + 1, "text": edge['label']} 
            for i, edge in enumerate(story_map_data['story_map']['edges']) if edge['from'] == 'start'
        ]
        
        scene_data = {
            "content": start_node['details'],
            "choices": initial_choices
        }

        # 4. Generate dynamic writing style (existing logic)
        writing_style = await _generate_dynamic_writing_style(client, story_type)

        return {
            "scene_data": scene_data,
            "writing_style": writing_style,
            "author": author,
            "title": title,
            "story_map": story_map_data['story_map']
        }
    ```

### 4. API 和 CRUD 层适配

*   **`app/crud/crud_game.py`**: 创建一个新函数 `update_game_meta`，用于一次性将 `author`, `title`, 和 `story_map` (JSON string) 保存到数据库。
*   **`app/api/v1/endpoints/game.py`**: 在 `start_game` 函数中，调用新的 `update_game_meta` 函数来保存数据，并在返回的 `GameStartResponse` 中包含这些新字段。

---

## 第二阶段：前端实现

### 1. 页面布局 (`templates/index.html`)

**修改方案:**

1.  在页面中添加一个用于显示作者和标题的区域。
2.  添加一个容器元素，用于渲染故事线路图。
3.  引入 Mermaid.js 库。

```html
<!-- templates/index.html -->

<!-- ... existing elements ... -->

<div class="text-center my-4">
    <h2 id="story-title" class="text-3xl font-bold"></h2>
    <p id="story-author" class="text-lg text-gray-400"></p>
</div>

<div id="story-map-container" class="my-8">
    <pre class="mermaid">
        <!-- Mermaid graph will be injected here -->
    </pre>
</div>

<!-- ... existing elements ... -->

<!-- Add Mermaid.js script -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
    mermaid.initialize({ startOnLoad: false });
</script>
<script src="/static/js/game.js"></script>
```

### 2. 前端逻辑 (`static/js/game.js`)

**修改方案:**

1.  **更新 `startGame` 函数**: 修改 `fetch` 请求成功后的处理逻辑，以接收并存储 `author`, `title`, 和 `story_map`。
2.  **创建 `renderStoryMap` 函数**: 这个新函数负责将接收到的 `story_map` JSON 数据转换为 Mermaid.js 的图表语法，并渲染到页面上。

```javascript
// static/js/game.js

async function startGame() {
    // ... (fetch call)
    const data = await response.json();
    
    // --- 更新UI ---
    document.getElementById('story-title').textContent = data.title;
    document.getElementById('story-author').textContent = `作者: ${data.author}`;
    
    renderStoryMap(data.story_map);
    // --- 结束 ---

    // ... (rest of the function)
}

function renderStoryMap(storyMap) {
    const { nodes, edges } = storyMap;
    let graphDefinition = 'graph TD;\n';

    nodes.forEach(node => {
        graphDefinition += `    ${node.id}["${node.label}"];\n`;
    });

    edges.forEach(edge => {
        graphDefinition += `    ${edge.from} -- "${edge.label}" --> ${edge.to};\n`;
    });

    const container = document.querySelector("#story-map-container .mermaid");
    container.textContent = graphDefinition;
    
    mermaid.run({
        nodes: [container]
    });
}
```

---

## 设计总览流程图

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend API
    participant Story Generator
    participant Database

    User->>Frontend: 选择故事类型并点击“开始”
    Frontend->>Backend API: POST /game (story_type)
    Backend API->>Story Generator: generate_initial_scene(story_type)
    
    Story Generator->>Story Generator: 随机生成作者和标题
    Story Generator->>LLM: 请求生成故事线路图 (JSON)
    LLM-->>Story Generator: 返回故事线路图 JSON
    
    Story Generator->>Story Generator: 提取初始场景
    Story Generator->>LLM: 请求生成写作风格
    LLM-->>Story Generator: 返回写作风格
    
    Story Generator-->>Backend API: 返回 {scene, style, author, title, story_map}
    
    Backend API->>Database: 创建 Game 记录
    Backend API->>Database: 保存 author, title, story_map, style
    Backend API->>Database: 保存初始 Scene
    
    Backend API-->>Frontend: 返回 {game_id, scene, author, title, story_map}
    
    Frontend->>Frontend: 更新UI (标题, 作者)
    Frontend->>Frontend: 调用 renderStoryMap()
    Frontend->>Mermaid.js: 渲染故事线路图