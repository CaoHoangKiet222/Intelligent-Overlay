from __future__ import annotations

import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError


logger = logging.getLogger(__name__)


class AnalysisTaskProducer:
	def __init__(self, *, bootstrap_servers: str, topic_tasks: str) -> None:
		self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
		self._topic_tasks = topic_tasks
		self._started = False
		self._available = False

	async def start(self) -> None:
		if self._started:
			return
		try:
			await self._producer.start()
			self._started = True
			self._available = True
			logger.info("Kafka analysis-task producer started successfully")
		except (KafkaConnectionError, Exception) as exc:
			logger.warning("Kafka producer unavailable: %s. Demo API will continue without async analyze.", exc)
			self._started = False
			self._available = False

	async def stop(self) -> None:
		if not self._started or not self._available:
			return
		try:
			await self._producer.stop()
			self._started = False
		except Exception as exc:
			logger.warning("Error stopping Kafka producer: %s", exc)

	async def publish(self, task: Dict[str, Any]) -> None:
		if not self._available:
			logger.warning("Kafka producer unavailable, skipping publish for event_id=%s", task.get("event_id"))
			return
		event_id = str(task.get("event_id") or "")
		if not event_id:
			logger.warning("Missing event_id in task payload, skipping publish")
			return
		try:
			key = event_id.encode("utf-8")
			value = json.dumps(task).encode("utf-8")
			await self._producer.send_and_wait(self._topic_tasks, key=key, value=value)
		except Exception as exc:
			logger.error("Failed to publish analysis task to Kafka: %s", exc)


