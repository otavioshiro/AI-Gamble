import openai
import json
import logging
import random
from typing import Dict, List, Optional

from app.core.config import settings

def _extract_json_from_string(text: str) -> Optional[str]:
    """
    Extracts a JSON object string from a larger string, cleaning up markdown.
    """
    if not text:
        return None
    
    if text.startswith("```json"):
        text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
    
    text = text.strip()
    first_bracket_pos = text.find('{')
    if first_bracket_pos == -1:
        return None
    last_bracket_pos = text.rfind('}')
    if last_bracket_pos == -1 or last_bracket_pos < first_bracket_pos:
        return None

    return text[first_bracket_pos:last_bracket_pos+1]


async def _generate_theme_details(client: openai.AsyncOpenAI, story_type: str) -> dict:
    """
    Generates representative authors and title keywords for a given story type using an LLM.
    """
    prompt = f"""
    你需要为一个'{story_type}'类型的故事，生成一些相关的创作元素。
    请严格按照以下JSON格式返回，不要有任何其他文字或markdown标记:
    {{
      "authors": ["作家A", "作家B", "作家C", "作家D", "作家E"],
      "title_keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5", "关键词6", "关键词7", "关键词8"]
    }}
    """
    logging.info(f"Generating theme details for story type: {story_type}")
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        content = response.choices[0].message.content
        json_str = _extract_json_from_string(content)
        if not json_str:
            raise ValueError("LLM returned no valid JSON for theme details.")
        
        theme_details = json.loads(json_str)
        if 'authors' in theme_details and 'title_keywords' in theme_details:
            logging.info(f"Successfully generated theme details for '{story_type}'.")
            return theme_details
    except Exception as e:
        logging.error(f"Failed to generate or parse theme details: {e}")

    logging.warning(f"Using fallback theme details for '{story_type}'.")
    return {
        "authors": ["一位神秘的作家", "佚名说书人"],
        "title_keywords": ["命运", "旅程", "秘密", "传说", "遗迹", "星辰"]
    }


async def _generate_dynamic_writing_style(client: openai.AsyncOpenAI, story_type: str, author: str, title: str) -> str:
    """
    Generates a dynamic and creative writing style persona using the LLM.
    """
    style_prompt = f"""
    你需要为一位创作'{story_type}'类型故事的AI作家，构思一个独特且富有创意的“作家身份”或“写作风格”。
    这个身份应该模仿著名作家'{author}'的风格，来讲述名为《{title}》的故事。
    这个身份描述应该非常简洁（一句话），富有想象力，并能直接用在给AI的指示中。
    请直接返回这个身份描述，不要任何多余的解释或引号。
    """
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": style_prompt}],
            temperature=1.0,
            max_tokens=150,
        )
        style = response.choices[0].message.content.strip().replace('"', '')
        if style:
            logging.info(f"Dynamically generated writing style: {style}")
            return style
    except Exception as e:
        logging.error(f"Failed to generate dynamic writing style: {e}")
    
    return f"你是一位模仿大师，正在以'{author}'的风格，讲述'{story_type}'故事《{title}》。"


async def generate_story_map(client: openai.AsyncOpenAI, story_type: str, author: str, title: str) -> dict:
    """
    Generates a complete story map including plot, key nodes, and endings.
    """
    prompt = f"""
    你是一位顶级的游戏叙事设计师。请为一部名为《{title}》、由'{author}'创作的'{story_type}'风格的互动小说，设计一个结构丰富、引人入胜的“故事蓝图”。

    **核心要求:**
    1.  **结构复杂性**: 故事蓝图必须具备非线性的特点。请设计一个包含**至少{settings.NODE_NUM}个关键节点**的结构，并确保其中有**明确的分支与汇合**的路径。
    2.  **完整节点**: 必须包含一个开端 (id: "start") 和至少两个不同的结局 (e.g., id: "end_good", id: "end_bad")。
    3.  **清晰连接**: 必须包含 `nodes` 和 `edges` 两个部分。`edges` 用于定义节点之间的所有连接，是构成故事流向的关键。
    4.  **内容质量**:
        *   节点的 `label` (标签) 应简短、有力，并能激发想象力 (例如：“风暴前夜”、“背叛者的低语”、“命运的十字路口”)。
        *   节点的 `details` (详情) 应提供具体、生动的场景或情境描述。
        *   边的 `label` (标签) 应是玩家将看到的具体选择，需要有悬念和吸引力。
    5.  **角色设定**: 故事必须包含一个有名字的主角和与主角有关联的角色，请在故事蓝图中体现他们的存在和关系。
    6.  **视角要求**: 故事应以小说第三人称视角来书写。
    7.  **严格的JSON格式**: 你的回答必须是严格的、单一的JSON对象，不要有任何其他文字或markdown标记。结构如下：
        ```json
        {{
          "nodes": [
            {{ "id": "start", "label": "故事开端", "details": "详细描述..." }},
            {{ "id": "node_1", "label": "关键抉择A", "details": "详细描述..." }},
            {{ "id": "node_2", "label": "风暴前夜", "details": "详细描述..." }},
            {{ "id": "node_3", "label": "命运的十字路口", "details": "详细描述..." }},
            {{ "id": "end_good", "label": "光明结局", "details": "详细描述..." }},
            {{ "id": "end_bad", "label": "黑暗结局", "details": "详细描述..." }}
          ],
          "edges": [
            {{ "from": "start", "to": "node_1", "label": "接受神秘的邀请" }},
            {{ "from": "start", "to": "node_2", "label": "忽略警告，独自调查" }},
            {{ "from": "node_1", "to": "node_3", "label": "相信盟友" }},
            {{ "from": "node_2", "to": "node_3", "label": "寻找古老的遗物" }},
            {{ "from": "node_3", "to": "end_good", "label": "做出最终的牺牲" }},
            {{ "from": "node_3", "to": "end_bad", "label": "屈服于力量的诱惑" }}
          ]
        }}
        ```

    请现在为《{title}》生成这个结构丰富的故事蓝图JSON对象。
    """
    logging.info(f"Generating story map for '{title}'...")
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        json_str = _extract_json_from_string(content)
        if not json_str:
            raise ValueError("LLM returned no valid JSON for story map.")

        story_map = json.loads(json_str)
        logging.info(f"Successfully generated story map for '{title}'.")
        return story_map
    except Exception as e:
        logging.error(f"Failed to generate or parse story map: {e}")
        return {
          "nodes": [
            { "id": "start", "label": "故事开端", "details": "在一个遥远的世界，一个未知的故事正等待着你..." },
            { "id": "node_1", "label": "探索", "details": "你向前走去，发现了两条岔路。" },
            { "id": "end_bad", "label": "迷失", "details": "你迷失在了无尽的黑暗中。" }
          ],
          "edges": [
            { "from": "start", "to": "node_1", "label": "向前探索。" },
            { "from": "node_1", "to": "end_bad", "label": "走左边的路。" }
          ]
        }

async def _generate_choices(client: openai.AsyncOpenAI, writing_style: str, story_map: dict, scene_content: str) -> List[Dict]:
    """
    Generates a list of choices for a given scene content.
    """
    prompt = f"""
    {writing_style} 你是一位互动小说家。
    **你的任务:**
    根据下面的“当前场景”和“故事蓝图”，为玩家生成3个引人入胜的后续选择。

    **核心要求:**
    1.  **多样性**: 选项应提供不同的方向（例如：调查、对话、行动）。
    2.  **参考蓝图**: 至少有一个选项应该巧妙地引导故事向“故事蓝图”中的某个节点发展。
    3.  **JSON输出**: 你的回答必须是严格的、单一的JSON对象，格式如下，不要有任何其他文字或markdown标记:
        {{
          "choices": [
            {{ "id": 1, "text": "第一个选项" }},
            {{ "id": 2, "text": "第二个选项" }},
            {{ "id": 3, "text": "第三个选项" }}
          ]
        }}

    **故事蓝图 (高层指引):**
    {json.dumps(story_map, ensure_ascii=False)}

    **当前场景:**
    {scene_content}

    请现在生成JSON对象。
    """
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        content = response.choices[0].message.content
        json_str = _extract_json_from_string(content)
        if not json_str:
            raise ValueError("LLM returned no valid JSON for choices.")
        
        data = json.loads(json_str)
        return data.get("choices", [])
    except Exception as e:
        logging.error(f"Failed to generate choices: {e}")
        return [{"id": 1, "text": "继续..."}]

async def generate_initial_scene(story_type: str) -> dict:
    """
    Generates the author, title, story map, initial scene, and writing style.
    """
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

    theme = await _generate_theme_details(client, story_type)
    author = random.choice(theme["authors"])
    system_prompt = f"""
    请直接返回小说名称，不要带引号或其他多余内容。
    """
    # 让AI生成小说名称，而不是随机拼接关键词
    title_prompt = f"""
    你需要为一个'{story_type}'类型的故事，生成一个富有吸引力且独特的小说名称。
    """

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        # messages=[{"role": "user", "content": title_prompt}],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": title_prompt}
        ],
        temperature=0.7,
    )
    title = response.choices[0].message.content.strip()
    if title == '':
        title = 'fuck gemini'
    story_map_data = await generate_story_map(client, story_type, author, title)
    writing_style = await _generate_dynamic_writing_style(client, story_type, author, title)

    try:
        start_node = next(node for node in story_map_data['nodes'] if node['id'] == 'start')
        initial_content = start_node['details']
    except (StopIteration, KeyError) as e:
        logging.error(f"Could not parse start node from story map: {e}. Using fallback.")
        initial_content = "在一个遥远的世界，一个未知的故事正等待着你..."

    # Generate choices for the initial scene
    initial_choices = await _generate_choices(client, writing_style, story_map_data, initial_content)

    scene_data = {
        "content": initial_content,
        "choices": initial_choices,
        "current_node_id": "start"
    }
    
    # The initial history only contains the first scene's content
    story_history = [{"role": "assistant", "content": initial_content}]

    return {
        "scene_data": scene_data,
        "writing_style": writing_style,
        "author": author,
        "title": title,
        "story_map": story_map_data,
        "story_history": story_history
    }


async def generate_next_scene(writing_style: str, story_map: dict, story_history: List[Dict], choice_text: str) -> dict:
    """
    Dynamically generates the next scene and choices based on history and player's choice.
    """
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

    story_history.append({"role": "user", "content": choice_text})

    system_prompt = f"""
    {writing_style} 你的任务是作为一名才华横溢的互动小说家，动态地推进故事并创造引人入胜的选择。

    **核心指令:**
    1.  **续写故事**: 基于“故事历史”和“玩家的最新选择”，创作下一段故事。
    2.  **生成选项**: 为新创作的情节生成3个多样化且有意义的选项。
    3.  **参考蓝图**: 时刻参考“故事蓝图”。在适当的时候，巧妙地设计一个选项，将故事引向蓝图中的下一个关键节点。
    4.  **严格的节点ID**: `current_node_id` 的值 **必须** 是“故事蓝图”中 `nodes` 列表里已存在的某个 `id`。这是强制性要求。
    5.  **角色设定**: 故事必须包含一个有名字的主角和与主角有关联的角色。
    6.  **视角要求**: 故事应以小说第三人称视角来书写。
    7.  **JSON输出**: 你的回答必须是严格的、单一的JSON对象，格式如下，不要有任何其他文字或markdown标记:
        {{
          "current_node_id": "从故事蓝图nodes中选择的最匹配的节点ID",
          "content": "你创作的下一段故事内容...",
          "choices": [
            {{ "id": 1, "text": "第一个选项" }},
            {{ "id": 2, "text": "第二个选项" }},
            {{ "id": 3, "text": "第三个选项" }}
          ]
        }}
    """
    recent_history = json.dumps(story_history[-6:], ensure_ascii=False)
    story_map_str = json.dumps(story_map, ensure_ascii=False)

    user_prompt = f"""
    **故事蓝图 (高层指引):**
    {story_map_str}

    **故事历史 (最近的对话):**
    {recent_history}

    **玩家的最新选择:**
    "{choice_text}"

    请根据以上所有信息，续写故事并生成新的选项。
    """

    try:
        logging.info("--- Generating next dynamic scene ---")
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,
        )
        
        raw_content = response.choices[0].message.content
        json_str = _extract_json_from_string(raw_content)
        if not json_str:
            raise ValueError("LLM returned no valid JSON for the next scene.")

        scene_data = json.loads(json_str)
        if 'content' not in scene_data or 'choices' not in scene_data or 'current_node_id' not in scene_data:
            raise ValueError("LLM response is missing required keys 'content', 'choices', or 'current_node_id'.")

        story_history.append({"role": "assistant", "content": scene_data["content"]})

        return {
            "scene_data": scene_data,
            "story_history": story_history
        }

    except Exception as e:
        logging.error(f"Failed to generate dynamic next scene: {e}")
        return {
            "scene_data": {
                "current_node_id": "start",
                "content": "一阵神秘的迷雾笼罩了你的思绪，让你回到了一个熟悉的地方。也许，命运给了你另一次机会。",
                "choices": [{"id": 1, "text": "重新审视周围的环境"}]
            },
            "story_history": story_history
        }