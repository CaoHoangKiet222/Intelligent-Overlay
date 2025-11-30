from shared.contracts import ContextChunk
from data.models import Segment


def segment_to_chunk(segment: Segment) -> ContextChunk:
	return ContextChunk(
		segment_id=str(segment.id),
		document_id=str(segment.document_id),
		text=segment.text,
		start_offset=segment.start_offset,
		end_offset=segment.end_offset,
		page_no=segment.page_no,
		paragraph_no=segment.paragraph_no,
		sentence_index=segment.sentence_no,
		speaker_label=segment.speaker_label,
		timestamp_start_ms=segment.timestamp_start_ms,
		timestamp_end_ms=segment.timestamp_end_ms,
		metadata={"position": segment.sentence_no},
	)

