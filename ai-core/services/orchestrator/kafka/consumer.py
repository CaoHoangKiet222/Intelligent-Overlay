import asyncio
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from app.config import KAFKA_BOOTSTRAP, KAFKA_GROUP, TOPIC_TASKS
from orchestration.orchestrator_service import OrchestratorService
import logging

logger = logging.getLogger(__name__)


async def serve(orch: OrchestratorService):
	try:
		consumer = AIOKafkaConsumer(
			TOPIC_TASKS,
			bootstrap_servers=KAFKA_BOOTSTRAP,
			group_id=KAFKA_GROUP,
			enable_auto_commit=False,
			auto_offset_reset="earliest",
			max_poll_interval_ms=300000,
		)
		await consumer.start()
		logger.info("Kafka consumer started successfully")
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
	except (KafkaConnectionError, Exception) as e:
		logger.warning(f"Kafka consumer unavailable: {e}. Service will continue but won't process tasks from Kafka.")
		# Keep the task running but just wait (service is still available for health checks)
		while True:
			await asyncio.sleep(60)  # Check every minute if Kafka becomes available


