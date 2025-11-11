import asyncio
from aiokafka import AIOKafkaConsumer
from config import KAFKA_BOOTSTRAP, KAFKA_GROUP, TOPIC_TASKS
from orchestration.orchestrator_service import OrchestratorService


async def serve(orch: OrchestratorService):
	consumer = AIOKafkaConsumer(
		TOPIC_TASKS,
		bootstrap_servers=KAFKA_BOOTSTRAP,
		group_id=KAFKA_GROUP,
		enable_auto_commit=False,
		auto_offset_reset="earliest",
		max_poll_interval_ms=300000,
	)
	await consumer.start()
	try:
		async for msg in consumer:
			try:
				await orch.handle_message(msg.value)
				await consumer.commit()
			except Exception:
				# keep offset uncommitted to retry later
				pass
	finally:
		await consumer.stop()


