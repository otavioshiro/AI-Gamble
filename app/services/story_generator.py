import openai
import json
import logging
import random
import time
from typing import Dict, List, Optional

from app.core.config import settings
from app.services.sse_service import redis_client
from app.crud import crud_game

async def _generate_story_concept(client: openai.AsyncOpenAI, story_type: str) -> dict:
    """
    Generates the core concept of the story (author, title, writing style) in a single LLM call.
    """
    prompt = f"""
    你需要为一个'{story_type}'类型的故事，生成一个包含作家、标题和写作风格的核心概念。
    请严格按照以下JSON格式返回，不要有任何其他文字或markdown标记:
    {{
      "author": "一个有代表性的作家名字",
      "title": "一个创意小说标题",
      "writing_style": "一句简洁且富有想象力的写作风格描述，可以直接用在给AI的指示中"
    }}
    """
    logging.info(f"Generating story concept for story type: {story_type}")
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        content = response.choices[0].message.content
        json_str = _extract_json_from_string(content)
        if not json_str:
            raise ValueError("LLM returned no valid JSON for story concept.")
        
        concept = json.loads(json_str)
        if 'author' in concept and 'title' in concept and 'writing_style' in concept:
            logging.info(f"Successfully generated story concept for '{story_type}'.")
            return concept
    except Exception as e:
        logging.error(f"Failed to generate or parse story concept: {e}")

    logging.warning(f"Using fallback story concept for '{story_type}'.")
    return {
        "author": "一位神秘的作家",
        "title": "失落的传说",
        "writing_style": "你是一位模仿大师，正在以一位神秘作家的风格，讲述一个关于失落传说的故事。"
    }


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


async def generate_story_map(client: openai.AsyncOpenAI, game_id: int, story_type: str, author: str, title: str) -> dict:
    """
    Generates a complete story map, streaming progress updates via Redis.
    """
    channel = f"game:{game_id}"
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
    logging.info(f"Generating story map for '{title}' (game_id: {game_id})...")
    full_content = ""
    last_publish_time = time.time()

    try:
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content or ""
                full_content += content
            
            current_time = time.time()
            if current_time - last_publish_time > 0.5:  # Publish every 0.5 seconds
                await redis_client.publish(channel, {
                    "event": "map_progress",
                    "status": "正在构建故事脉络..."
                })
                last_publish_time = current_time

        json_str = _extract_json_from_string(full_content)
        if not json_str:
            raise ValueError("LLM returned no valid JSON for story map.")

        story_map = json.loads(json_str)
        logging.info(f"Successfully generated story map for '{title}'.")
        return story_map
    except Exception as e:
        logging.error(f"Failed to generate or parse story map: {e}")
        await redis_client.publish(channel, {
            "event": "error",
            "message": "故事生成失败，请稍后再试。"
        })
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

async def generate_initial_scene(game_id: int, story_type: str, db_session):
    """
    Asynchronously generates the initial scene, updates the database, and publishes the result via Redis.
    This function is designed to be run as a background task.
    """
    channel = f"game:{game_id}"
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

    try:
        # Step 1: Generate core concept
        await redis_client.publish(channel, {"event": "map_progress", "status": "正在构思故事核心..."})
        concept = await _generate_story_concept(client, story_type)
        author = concept["author"]
        title = concept["title"]
        writing_style = concept["writing_style"]

        # Step 2: Generate story map with progress streaming
        await redis_client.publish(channel, {"event": "map_progress", "status": "正在构建世界地图..."})
        story_map_data = await generate_story_map(client, game_id, story_type, author, title)

        # Step 3: Generate initial scene and choices
        await redis_client.publish(channel, {"event": "map_progress", "status": "故事即将开始...马上就好..."})
        start_node = next(node for node in story_map_data['nodes'] if node['id'] == 'start')
        initial_content = start_node['details']
        
        initial_choices = await _generate_choices(client, writing_style, story_map_data, initial_content)

        scene_data = {
            "content": initial_content,
            "choices": initial_choices,
            "current_node_id": "start"
        }
        
        story_history = [{"role": "assistant", "content": initial_content}]

        # Final payload
        # --- Refactored Data Publishing ---

        # First, update the database with all generated data.
        game_update_data = crud_game.GameUpdateSchema(
            writing_style=writing_style,
            author=author,
            title=title,
            story_map=json.dumps(story_map_data, ensure_ascii=False),
            story_history=json.dumps(story_history, ensure_ascii=False),
            current_scene_json=json.dumps(scene_data, ensure_ascii=False)
        )
        await crud_game.update_game(db_session, game_id=game_id, game_in=game_update_data)
        logging.info(f"Successfully updated game {game_id} in the database.")

        # Now, publish the data in smaller, separate chunks.
        
        # Chunk 1: Send the story map first.
        await redis_client.publish(channel, {
            "event": "story_map_ready",
            "data": {
                "story_map": story_map_data
            }
        })
        logging.info(f"Published story_map_ready for game {game_id}")

        # Chunk 2: Send the initial scene and other core info.
        initial_scene_payload = {
            "scene_data": scene_data,
            "author": author,
            "title": title,
            "story_history": story_history
        }
        await redis_client.publish(channel, {
            "event": "initial_scene_ready",
            "data": initial_scene_payload
        })
        logging.info(f"Published initial_scene_ready for game {game_id}")
        logging.info(f"Successfully generated and published initial scene for game {game_id}")

    except Exception as e:
        logging.error(f"Error during initial scene generation for game {game_id}: {e}")
        await redis_client.publish(channel, {
            "event": "error",
            "message": f"故事生成失败: {e}"
        })


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
