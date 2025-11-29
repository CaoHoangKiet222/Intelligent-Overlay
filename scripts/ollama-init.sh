#!/bin/sh

set -e

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

echo "🚀 Starting Ollama model preloader..."
echo "OLLAMA_HOST: $OLLAMA_HOST"

# Models được chọn tối ưu cho GPU 4GB:
# - phi3:mini: Model chính cho generation tasks, nhẹ (~2.3GB), chất lượng tốt cho general purpose
# - qwen3-embedding:0.6b: Embedding model chất lượng cao (1024 dim), tốt cho retrieval và semantic search
MODELS="phi3:mini qwen3-embedding:0.6b"

wait_for_ollama() {
  echo "⏳ Waiting for Ollama to be ready..."
  i=1
  while [ $i -le 30 ]; do
    if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
      echo "✅ Ollama is ready!"
      return 0
    fi
    echo "   Attempt $i/30..."
    i=$((i + 1))
    sleep 2
  done
  echo "❌ Ollama did not become ready in time"
  return 1
}

pull_model() {
  model=$1
  echo ""
  echo "📥 Pulling model: $model"
  if curl -X POST "$OLLAMA_HOST/api/pull" -d "{\"name\": \"$model\"}" -H "Content-Type: application/json" --no-buffer 2>&1 | grep -q '"status":"success"'; then
    echo "✅ Successfully pulled: $model"
    return 0
  else
    echo "⚠️  Failed to pull $model, continuing..."
    return 1
  fi
}

wait_for_ollama

for model in $MODELS; do
  pull_model "$model"
done

echo ""
echo "🎉 All models preloaded successfully!"
echo ""
echo "📋 Available models:"
curl -s "$OLLAMA_HOST/api/tags" || echo "Could not list models"

