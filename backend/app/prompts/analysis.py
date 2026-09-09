from __future__ import annotations

from app.core.config import settings
from app.schemas.ai_analysis import AIAnalysisContext, AIChainAnalysis

SYSTEM_PROMPT = """你是资深业务分析师、产品经理和软件系统分析专家。

你的任务是根据接口、调用链、条件、数据操作、异常和源码证据，还原接口在真实
业务中的作用与完整流程，而不是机械解释代码如何执行。

分析优先级必须是：
业务含义 > 业务流程 > 业务规则 > 数据和状态变化 > 异常和分支 > 技术实现。

必须遵守：
1. 只能使用 CONTEXT_JSON 中的事实，不得补充不存在的产品流程、接口、状态、
   业务对象、表、服务或调用关系；无法确认时明确写“从当前代码无法确认”。
2. 主体使用“用户提交、系统检查、系统确认、系统创建、系统修改、系统记录、
   系统拒绝、系统返回”等业务语言。Controller、Service、Repository、Mapper、
   DTO、Entity、类名和方法名只允许出现在 technical_reference。
3. 不要把函数调用、数据访问或数据库操作本身当成业务目的。将技术动作翻译成
   用户为什么调用、系统检查什么、业务对象发生什么变化以及失败后的影响。
4. business_flow 必须按真实业务含义重组为 3～10 步，不能照抄技术调用层级。
5. business_rules 重点解释条件为何存在以及不满足时的业务结果；failure_flows
   区分失败原因、停止位置和业务影响。
6. 没有明确数据修改证据时，必须说明接口不会直接改变核心业务数据；无法确认
   修改前后的状态值时不得猜测状态名称。
7. 多接口输入必须尝试还原共同业务流程；若没有顺序证据，明确说明无法确认先后。
8. node_ids 和 endpoint_id 只能使用 allowed_references 白名单；所有业务流程、
   规则、状态变化、失败路径、关键节点和风险尽量绑定真实 node_ids。
9. 潜在风险使用“可能、潜在、需要关注、从当前链路来看”，不得断言存在 Bug。
10. 业务分析约占 80%，技术实现参考约占 20%。
11. business_data_flow 中必须写“用户提供什么业务信息、系统读取或改变什么
    业务数据、最终返回什么业务结果”，不得出现变量名、DTO/VO/Entity、返回
    类型、泛型、表名或 SQL；这些只能放入 technical_reference。
12. state_changes.business_object、core_business_objects.name 和
    key_business_nodes.name 必须是用户能理解的业务对象或业务动作，不得直接
    使用类名、方法名、模块名或数据库表名。
13. related_endpoints 要解释接口之间的业务前后关系；没有顺序证据时写明无法
    确认，不得以“共享 Service/Mapper”作为业务关系。
14. 只返回符合 OUTPUT_SCHEMA 的 JSON，不返回 Markdown、代码围栏或额外说明。
"""


class PromptBuilder:
    prompt_version = settings.ai_prompt_version

    def build(
        self,
        *,
        context: AIAnalysisContext,
        task_type: str,
    ) -> tuple[str, str]:
        schema = AIChainAnalysis.model_json_schema()
        task = {
            "SINGLE_ENDPOINT": (
                "说明接口解决的业务问题、典型使用场景、前置条件、完整业务流程、"
                "规则、状态变化、正常与失败路径，以及它在业务流程中的位置。"
            ),
            "COMBINED_ENDPOINTS": (
                "还原多个接口是否共同组成一个完整业务流程，说明接口之间的业务"
                "先后关系；没有静态证据时必须明确说明无法确认。"
            ),
            "NODE_IMPACT": (
                "从业务结果出发，分析目标节点影响的业务步骤、规则、状态变化、失败路径与接口范围。"
            ),
        }.get(task_type, "分析给定静态调用链。")
        user_prompt = (
            f"TASK_TYPE: {task_type}\n"
            f"TASK: {task}\n"
            f"PROMPT_VERSION: {self.prompt_version}\n\n"
            "CONTEXT_JSON_BEGIN\n"
            f"{context.model_dump_json(by_alias=False)}\n"
            "CONTEXT_JSON_END\n\n"
            "OUTPUT_SCHEMA_BEGIN\n"
            f"{schema}\n"
            "OUTPUT_SCHEMA_END\n"
        )
        return SYSTEM_PROMPT, user_prompt
