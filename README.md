# 📖 AI 互动小说生成器

这是一个基于大型语言模型（LLM）的动态互动小说游戏。它能够根据玩家选择的故事类型，实时生成独特的故事情节、人物、以及一个可视化的故事发展线路图，为玩家提供一个充满未知和选择的沉浸式阅读体验。

---

## ✨ 核心功能

*   **🤖 动态故事生成**: 游戏的核心由 AI 驱动，能够根据预设的文学风格（如“东方玄幻”、“西方魔幻”）动态创作故事的开篇、发展和多重结局。
*   **🎲 随机化作家与作品**: 每次开启新游戏，系统都会随机生成符合所选类型的“作家”和“书名”，增加游戏的趣味性和代入感。
*   **🗺️ 可视化故事线路图**: 在游戏开始时，后端会预先生成整个故事的结构图（Story Map），并通过 [Mermaid.js](https://mermaid-js.github.io/mermaid/#/) 在前端渲染，让玩家可以直观地看到故事的潜在分支和结局。
*   **🌿 分支叙事**: 玩家的每一个选择都会影响故事的走向，导向不同的情节分支和最终结局。
*   **🎨 动态写作风格**: AI 会根据故事类型生成独特的写作风格描述，并应用于整个故事的叙述中，增强沉浸感。

---

## 🛠️ 技术栈

| 分类      | 技术                                                                                             |
| :-------- | :----------------------------------------------------------------------------------------------- |
| **后端**  | [**FastAPI**](https://fastapi.tiangolo.com/) - 高性能的 Python Web 框架。                          |
|           | [**SQLAlchemy**](https://www.sqlalchemy.org/) & [**SQLModel**](https://sqlmodel.tiangolo.com/) - 数据库交互和对象关系映射 (ORM)。 |
|           | [**Redis**](https://redis.io/) - 用于缓存和 Server-Sent Events (SSE) 消息队列。                    |
| **前端**  | [**Vanilla JavaScript**](http://vanilla-js.com/) - 无框架的纯原生 JavaScript，用于核心交互逻辑。 |
|           | [**Tailwind CSS**](https://tailwindcss.com/) - 一个功能类优先的 CSS 框架，用于快速构建界面。       |
|           | [**Mermaid.js**](https://mermaid-js.github.io/mermaid/#/) - 用于将文本和代码转换为流程图和可视化图表。 |
| **AI**    | [**OpenAI GPT**](https://openai.com/) - 作为故事生成的核心引擎。                                   |
| **部署**  | [**Docker**](https://www.docker.com/) & [**Docker Compose**](https://docs.docker.com/compose/) - 用于容器化部署和管理应用服务。 |

---

## 📂 项目结构

```
.
├── app/                # FastAPI 后端应用核心代码
│   ├── api/            # API 路由和端点
│   ├── crud/           # 数据库增删改查操作
│   ├── models/         # SQLAlchemy 数据模型
│   ├── schemas/        # Pydantic 数据校验模型
│   ├── services/       # 核心业务逻辑（如故事生成）
│   ├── main.py         # FastAPI 应用入口
│   └── database.py     # 数据库连接与初始化
├── static/             # 静态文件（CSS, JS, 图片）
├── templates/          # HTML 模板
├── .env.example        # 环境变量示例文件
├── .gitignore          # Git 忽略配置文件
├── DESIGN.md           # 系统设计文档
├── docker-compose.yml  # Docker 服务编排
├── Dockerfile          # Web 服务的 Docker 镜像配置
└── README.md           # 本文档
```

---

## 🚀 快速开始

通过 Docker，你可以轻松地在本地运行本项目。

**先决条件**:
*   已安装 [Docker](https://www.docker.com/get-started) 和 [Docker Compose](https://docs.docker.com/compose/install/)。

**配置**:

1.  **创建环境变量文件**:
    项目使用 `.env` 文件来管理敏感配置。我们提供了一个示例文件 `.env.example`，您可以复制它来创建自己的配置文件：
    ```bash
    # 在 Windows 上使用 copy
    copy .env.example .env

    # 在 macOS/Linux 上使用 cp
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**:
    打开新创建的 `.env` 文件，并填入您的 OpenAI API 密钥以及其他可能需要修改的配置。

**启动步骤**:

1.  **构建并启动服务**:
    在项目根目录下运行以下命令：
    ```bash
    docker-compose up --build
    ```

2.  **编译前端样式 (可选)**:
    如果你需要修改前端样式，可以打开一个新的终端，运行 `npm` 脚本来实时监听和编译 `tailwind.css`：
    ```bash
    npm run build
    ```

3.  **访问应用**:
    打开浏览器，访问 `http://localhost:1888` 即可开始游戏。

---

## 🌐 API 端点

项目提供了一组 RESTful API 来管理游戏状态。

| 方法   | 路径                           | 描述                               |
| :----- | :----------------------------- | :--------------------------------- |
| `POST` | `/api/v1/game`                 | 创建一个新游戏，返回初始场景和故事图。 |
| `POST` | `/api/v1/game/{game_id}/choice`| 提交玩家的选择，获取下一个场景。   |
| `GET`  | `/api/v1/game/{game_id}`       | 获取指定游戏的当前完整状态。       |
| `DELETE`| `/api/v1/game/{game_id}`      | 删除一个游戏会话。                 |

---

## ⚙️ 工作流程

下图简要描述了从玩家开始游戏到故事内容呈现的完整流程：

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端 (JS)
    participant Backend as 后端 (FastAPI)
    participant StoryGen as 故事生成服务
    participant LLM as AI 大语言模型
    participant DB as 数据库

    User->>Frontend: 选择故事类型，点击“开始”
    Frontend->>Backend: POST /api/v1/game
    Backend->>StoryGen: generate_initial_scene()
    StoryGen->>LLM: 请求生成故事线路图 (JSON)
    LLM-->>StoryGen: 返回完整故事结构
    StoryGen->>DB: 保存故事元数据 (作者, 标题, 线路图)
    StoryGen-->>Backend: 返回初始场景数据
    Backend-->>Frontend: 返回 {game_id, scene, author, title, story_map}
    Frontend->>Mermaid.js: 渲染故事线路图
    Frontend->>User: 显示初始场景和线路图