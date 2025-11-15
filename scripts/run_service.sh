#!/bin/bash

SERVICE_NAME=${1:-""}
PORT=${2:-""}
MODE=${3:-"foreground"}

get_service_port() {
	case "$1" in
		"model-adapter") echo "8081" ;;
		"prompt-service") echo "8082" ;;
		"retrieval-service") echo "8083" ;;
		"agent-service") echo "8084" ;;
		"orchestrator") echo "8085" ;;
		*) echo "" ;;
	esac
}

get_service_path() {
	case "$1" in
		"model-adapter") echo "ai-core/services/model-adapter" ;;
		"prompt-service") echo "ai-core/services/prompt-service" ;;
		"retrieval-service") echo "ai-core/services/retrieval-service" ;;
		"agent-service") echo "ai-core/services/agent-service" ;;
		"orchestrator") echo "ai-core/services/orchestrator" ;;
		*) echo "" ;;
	esac
}

run_service() {
	local service_name=$1
	local port=$2
	local mode=$3
	
	local service_path=$(get_service_path "$service_name")
	if [ -z "$service_path" ]; then
		echo "✗ Unknown service: $service_name"
		echo "Available services: model-adapter, prompt-service, retrieval-service, agent-service, orchestrator"
		return 1
	fi
	
	if [ ! -d "$service_path" ]; then
		echo "✗ Service directory not found: $service_path"
		return 1
	fi
	
	if [ -z "$port" ]; then
		port=$(get_service_port "$service_name")
	fi
	
	if lsof -ti:$port > /dev/null 2>&1; then
		local pid=$(lsof -ti:$port)
		echo "⚠ Port $port is already in use by PID $pid"
		echo "   Stop it first: kill $pid"
		echo "   Or use different port: $0 $service_name <custom_port>"
		return 1
	fi
	
	# Get absolute path to service directory (from scripts/ folder)
	local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
	local project_root="$(cd "$script_dir/.." && pwd)"
	local full_service_path="$project_root/$service_path"
	
	cd "$full_service_path" || return 1
	
	# Load environment variables from .env file
	if [ -f ".env" ]; then
		echo "→ Loading environment from .env file..."
		set -a
		source .env
		set +a
	elif [ -f "env.example" ]; then
		echo "⚠ .env file not found, creating from env.example..."
		cp env.example .env
		# Convert Docker service names to localhost for local development
		# Use sed compatible with both GNU and BSD (macOS)
		if [[ "$OSTYPE" == "darwin"* ]]; then
			sed -i '' 's/broker:9092/localhost:9092/g' .env
			sed -i '' 's/@postgres:/@localhost:/g' .env
			sed -i '' 's|redis://redis:|redis://localhost:|g' .env
			sed -i '' 's|http://model-adapter:8000|http://localhost:8081|g' .env
			sed -i '' 's|http://prompt-service:8000|http://localhost:8082|g' .env
			sed -i '' 's|http://retrieval-service:8000|http://localhost:8083|g' .env
			sed -i '' 's|ray-head:6379|localhost:6379|g' .env
			# Set RAY_ADDRESS to empty for local development (starts new local instance)
			sed -i '' 's/^RAY_ADDRESS=auto/RAY_ADDRESS=/' .env
		else
			sed -i 's/broker:9092/localhost:9092/g' .env
			sed -i 's/@postgres:/@localhost:/g' .env
			sed -i 's|redis://redis:|redis://localhost:|g' .env
			sed -i 's|http://model-adapter:8000|http://localhost:8081|g' .env
			sed -i 's|http://prompt-service:8000|http://localhost:8082|g' .env
			sed -i 's|http://retrieval-service:8000|http://localhost:8083|g' .env
			sed -i 's|ray-head:6379|localhost:6379|g' .env
			# Set RAY_ADDRESS to empty for local development (starts new local instance)
			sed -i 's/^RAY_ADDRESS=auto/RAY_ADDRESS=/' .env
		fi
		echo "→ Created .env file with localhost values"
		set -a
		source .env
		set +a
	else
		echo "✗ No .env or env.example found for $service_name"
		echo "  Please create a .env file in $service_path"
		return 1
	fi
	
	if [ ! -d ".venv" ]; then
		echo "⚠ Virtual environment not found. Creating..."
		python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
	fi
	
	source .venv/bin/activate
	
	if ! python3 -c "import fastapi" 2>/dev/null; then
		echo "⚠ Dependencies not installed. Installing..."
		pip install -q -r requirements.txt
	fi
	
	export PORT=$port
	
	if [ "$mode" = "background" ]; then
		echo "→ Starting $service_name on port $port (background mode)..."
		nohup python3 -m app.main > /tmp/${service_name}.log 2>&1 &
		local pid=$!
		sleep 2
		if kill -0 $pid 2>/dev/null; then
			echo "✓ $service_name started on port $port (PID: $pid)"
			echo "  Logs: tail -f /tmp/${service_name}.log"
			echo "  Health: curl http://localhost:$port/healthz"
		else
			echo "✗ Failed to start $service_name. Check logs: tail /tmp/${service_name}.log"
			return 1
		fi
	else
		echo "→ Starting $service_name on port $port..."
		echo "  Press Ctrl+C to stop"
		echo ""
		python3 -m app.main
	fi
}

show_usage() {
	echo "Usage: $0 [service_name] [port] [mode]"
	echo ""
	echo "Services:"
	echo "  model-adapter (port 8081)"
	echo "  prompt-service (port 8082)"
	echo "  retrieval-service (port 8083)"
	echo "  agent-service (port 8084)"
	echo "  orchestrator (port 8085)"
	echo ""
	echo "Environment:"
	echo "  Script automatically loads .env file from service directory"
	echo "  If .env not found, creates it from env.example with localhost values"
	echo "  Each service has its own .env file with local development settings"
	echo ""
	echo "Examples:"
	echo "  $0 orchestrator                    # Run orchestrator on default port 8085"
	echo "  $0 orchestrator 8000                # Run orchestrator on port 8000"
	echo "  $0 orchestrator 8000 background     # Run in background mode"
	echo "  $0 agent-service 8084              # Run agent-service on port 8084"
	echo ""
	echo "Modes:"
	echo "  foreground  - Run in foreground (default, Ctrl+C to stop)"
	echo "  background  - Run in background (logs to /tmp/<service>.log)"
}

if [ -z "$SERVICE_NAME" ]; then
	show_usage
	exit 1
fi

run_service "$SERVICE_NAME" "$PORT" "$MODE"

