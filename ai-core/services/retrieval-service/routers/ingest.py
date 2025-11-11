from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from domain.schemas import IngestRequest, IngestResponse
from domain.segmentation import segment_text
from domain.pdf_reader import extract_pdf_text
from clients.model_adapter import embed_texts
from data.db import SessionLocal
from data.repositories import create_document, bulk_insert_segments, bulk_insert_embeddings


router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest(payload: IngestRequest = Depends(), pdf: UploadFile | None = File(default=None)):
	if payload.source_type == "pdf":
		if not pdf:
			raise HTTPException(status_code=400, detail="pdf file required")
		raw = await pdf.read()
		text = extract_pdf_text(raw)
	elif payload.source_type == "text":
		if not payload.text:
			raise HTTPException(status_code=400, detail="text required")
		text = payload.text
	else:
		if not payload.transcript:
			raise HTTPException(status_code=400, detail="transcript required")
		text = " ".join([x["text"] for x in payload.transcript])

	segs = segment_text(text, max_chars=payload.max_chars_per_segment, overlap=payload.overlap_chars)
	if not segs:
		raise HTTPException(status_code=400, detail="no segments produced")

	em = await embed_texts([s["text"] for s in segs])
	vectors = em.get("vectors") or []
	model = em.get("model", "")
	dim = em.get("dim", 1536)

	async with SessionLocal() as s:
		doc = await create_document(
			s,
			{
				"source_type": payload.source_type,
				"source_url": payload.url,
				"title": payload.title,
				"locale": payload.locale,
			},
		)
		seg_models = await bulk_insert_segments(s, doc.id, segs)
		emb_rows = []
		for seg, vec in zip(seg_models, vectors):
			emb_rows.append({"segment_id": seg.id, "model": model, "dim": dim, "vector": vec})
		if emb_rows:
			await bulk_insert_embeddings(s, emb_rows)

	return IngestResponse(document_id=str(doc.id), segments_created=len(segs), embedding_model=model, dim=dim)


