"""NPC Agent 业务逻辑

实现 NPC 相关 Agent 的核心功能
"""
from .models import NPCAgentRequest, NPCAgentResponse


class NPCService:
    """NPC 服务类"""
    
    @staticmethod
    async def process(request: NPCAgentRequest) -> NPCAgentResponse:
        """处理 NPC Agent 请求
        
        TODO: 实现实际的 NPC 逻辑
        """
        # 占位符实现
        return NPCAgentResponse(
            response="这是一个占位符响应，NPC 功能待定义",
            metadata={"status": "placeholder"}
        )


# 创建服务实例
npc_service = NPCService()
