import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.repositories.agent_repository import AgentRepository
from yuxi.repositories.agent_run_repository import AgentRunRepository
from yuxi.repositories.conversation_repository import ConversationRepository
from yuxi.services.run_queue_service import get_arq_pool
from yuxi.storage.postgres.models_business import Message, ScheduleDefinition, ScheduleLog
from yuxi.utils import logger


class ScheduleTriggerError(Exception):
    """定时任务触发异常"""

    pass


class ScheduleService:
    """定时任务触发相关核心业务服务层"""

    async def _build_and_enqueue_run(
        self,
        *,
        schedule: ScheduleDefinition,
        db: AsyncSession,
        title: str,
    ) -> tuple[str, str]:
        """在给定会话内创建对话、输入消息与 AgentRun，并推入 ARQ 队列。

        对齐 main 分支「统一 run 提交」契约（feat/unify-run-submission）：run 的输入正文
        由 Message 承载，run 仅登记元数据，并通过 agent_slug / uid 定位智能体与用户。
        schedule.user_id 存的是归属用户的 uid，与 run.uid、Agent.created_by 保持一致。

        本方法只 flush 不提交；提交由调用方负责（手动触发由路由提交，Cron 轮询由
        create_scheduled_run 提交），以隔离 T2 事务生命周期。
        """
        # 1. 解析 agent_config 获取 agent slug（Agent.slug 即旧 AgentConfig.agent_id）
        config_repo = AgentRepository(db)
        config_item = await config_repo.get_by_id(id=schedule.agent_config_id)
        if config_item is None:
            raise ScheduleTriggerError(f"agent_config {schedule.agent_config_id} 不存在")

        agent_slug = config_item.slug
        owner_uid = str(schedule.user_id)

        # 2. 创建对话（Thread）
        thread_id = str(uuid.uuid4())
        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.add_conversation(
            uid=owner_uid,
            agent_id=agent_slug,
            title=title,
            thread_id=thread_id,
            metadata={"agent_config_id": schedule.agent_config_id, "schedule_id": schedule.id},
        )

        # 3. 落库输入消息：run 的输入正文由 Message 承载，process_agent_run 从这里恢复 query/图片
        request_id = str(uuid.uuid4())
        message = Message(
            conversation_id=conversation.id,
            role="user",
            content=schedule.query,
            message_type="text",
            image_content=schedule.image_content,
            request_id=request_id,
            delivery_status="complete",
            extra_metadata={"source": "schedule", "scheduled": True, "auto_approve": True},
        )
        db.add(message)
        await db.flush()

        # 4. 登记 AgentRun（仅元数据）
        run_id = str(uuid.uuid4())
        input_payload = {
            "model_spec": None,
            "tool_approval_mode": None,
            "scheduled": True,
            "auto_approve": True,
        }
        run_repo = AgentRunRepository(db)
        await run_repo.create_run(
            run_id=run_id,
            conversation_thread_id=thread_id,
            agent_slug=agent_slug,
            uid=owner_uid,
            request_id=request_id,
            input_payload=input_payload,
            run_type="chat",
            input_message_id=message.id,
            conversation_id=conversation.id,
            source="schedule",
        )

        await db.flush()

        # 5. 入队 ARQ 队列
        queue = await get_arq_pool()
        await queue.enqueue_job("process_agent_run", run_id, _job_id=f"run:{run_id}")
        return thread_id, run_id

    async def create_scheduled_run(
        self,
        *,
        schedule: ScheduleDefinition,
        db: AsyncSession,
    ) -> tuple[str, str]:
        """
        为定时任务创建新对话(Thread)与运行任务(AgentRun)并推入ARQ队列。
        本方法由隔离事务(T2)对应的独立 Session 调用，内部执行 commit / rollback。
        """
        try:
            thread_id, run_id = await self._build_and_enqueue_run(
                schedule=schedule, db=db, title=f"[定时] {schedule.name}"
            )
            # 提交 T2 子事务
            await db.commit()
            return thread_id, run_id
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create scheduled run for schedule {schedule.id}: {e}")
            raise ScheduleTriggerError(str(e)) from e

    async def manual_trigger_schedule(
        self,
        *,
        schedule: ScheduleDefinition,
        db: AsyncSession,
    ) -> tuple[str, str]:
        """
        手动立即触发定时任务。由于是手动触发，不属于后台 Cron 轮询热路径，
        可以直接在当前的 Session 事务中执行，但逻辑与 create_scheduled_run 保持一致。
        事务提交由调用方（HTTP 路由）负责。
        """
        thread_id, run_id = await self._build_and_enqueue_run(
            schedule=schedule, db=db, title=f"[手动触发] {schedule.name}"
        )

        # 写入触发日志（由调用方提交事务）
        log = ScheduleLog(
            id=str(uuid.uuid4()),
            schedule_id=schedule.id,
            run_id=run_id,
            thread_id=thread_id,
            status="triggered",
            execution_status="pending",
            trigger_delay_ms=0,
            created_at=datetime.now(UTC),
        )
        db.add(log)

        return thread_id, run_id
