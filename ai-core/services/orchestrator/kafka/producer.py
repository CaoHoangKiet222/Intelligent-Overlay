from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from app.config import KAFKA_BOOTSTRAP, TOPIC_DLQ
import json
import logging

logger = logging.getLogger(__name__)


class DlqProducer:
	def __init__(self) -> None:
		self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
		self._started = False
		self._available = False

	async def start(self) -> None:
		if not self._started:
			try:
				await self.producer.start()
				self._started = True
				self._available = True
				logger.info("Kafka DLQ producer started successfully")
			except (KafkaConnectionError, Exception) as e:
				logger.warning(f"Kafka DLQ producer unavailable: {e}. Service will continue without DLQ.")
				self._started = False
				self._available = False

	async def stop(self) -> None:
		if self._started and self._available:
			try:
				await self.producer.stop()
				self._started = False
			except Exception as e:
				logger.warning(f"Error stopping Kafka producer: {e}")

	async def publish(self, event_id: str, payload: dict, reason: str) -> None:
		if not self._available:
			logger.warning(f"DLQ unavailable, skipping publish for event_id: {event_id}, reason: {reason}")
			return
		try:
			key = event_id.encode("utf-8")
			val = json.dumps({"event_id": event_id, "payload": payload, "reason": reason}).encode("utf-8")
			await self.producer.send_and_wait(TOPIC_DLQ, value=val, key=key)
		except Exception as e:
			logger.error(f"Failed to publish to DLQ: {e}")


