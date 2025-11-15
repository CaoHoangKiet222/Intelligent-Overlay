#!/bin/bash

SERVICE_NAME=${1:-"all"}
PORT=${2:-""}

check_service() {
	local port=$1
	local service_name=$2
	
	if lsof -ti:$port > /dev/null 2>&1; then
		local pid=$(lsof -ti:$port)
		local process=$(ps -p $pid -o comm= 2>/dev/null | head -1)
		if curl -s -f http://localhost:$port/healthz > /dev/null 2>&1; then
			echo "✓ $service_name is running on port $port (PID: $pid, Process: $process)"
			echo "  Health: http://localhost:$port/healthz"
			echo "  Metrics: http://localhost:$port/metrics"
			return 0
		else
			echo "⚠ $service_name process exists on port $port but health check failed (PID: $pid)"
			return 1
		fi
	else
		echo "✗ $service_name is not running on port $port"
		return 1
	fi
}

check_all_services() {
	echo "Checking all AI Core services..."
	echo "================================"
	
	check_service 8081 "Model Adapter"
	check_service 8082 "Prompt Service"
	check_service 8083 "Retrieval Service"
	check_service 8084 "Agent Service"
	check_service 8085 "Orchestrator"
	
	echo "================================"
	echo ""
	echo "Quick commands:"
	echo "  ./scripts/check_service.sh all              # Check all services"
	echo "  ./scripts/check_service.sh orchestrator 8000 # Check specific service"
	echo "  lsof -ti:8000                       # Find process on port"
	echo "  curl http://localhost:8000/healthz  # Manual health check"
}

if [ "$SERVICE_NAME" = "all" ]; then
	check_all_services
elif [ -n "$PORT" ]; then
	check_service $PORT "$SERVICE_NAME"
else
	echo "Usage: $0 [service_name] [port]"
	echo "Examples:"
	echo "  $0 all                    # Check all services"
	echo "  $0 orchestrator 8000      # Check specific service on port"
	echo "  $0 agent-service 8084     # Check agent service"
	exit 1
fi

