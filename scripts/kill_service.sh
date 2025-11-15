#!/bin/bash

SERVICE_NAME=${1:-""}
PORT=${2:-""}

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

kill_service() {
	local service_name=$1
	local port=$2
	
	if [ -z "$port" ]; then
		port=$(get_service_port "$service_name")
	fi
	
	if [ -z "$port" ]; then
		echo "✗ Invalid service or port: $service_name"
		return 1
	fi
	
	if ! lsof -ti:$port > /dev/null 2>&1; then
		echo "✗ No process running on port $port"
		return 1
	fi
	
	local pid=$(lsof -ti:$port)
	local process=$(ps -p $pid -o comm= 2>/dev/null | head -1)
	
	echo "→ Stopping service on port $port (PID: $pid, Process: $process)..."
	
	if kill $pid 2>/dev/null; then
		sleep 1
		if kill -0 $pid 2>/dev/null; then
			echo "⚠ Process still running, force killing..."
			kill -9 $pid 2>/dev/null
			sleep 1
		fi
		
		if ! kill -0 $pid 2>/dev/null; then
			echo "✓ Service stopped on port $port"
			return 0
		else
			echo "✗ Failed to stop service on port $port"
			return 1
		fi
	else
		echo "✗ Failed to kill process $pid"
		return 1
	fi
}

kill_all_services() {
	echo "Stopping all AI Core services..."
	echo "================================"
	
	kill_service "model-adapter" 8081
	kill_service "prompt-service" 8082
	kill_service "retrieval-service" 8083
	kill_service "agent-service" 8084
	kill_service "orchestrator" 8085
	
	echo "================================"
	echo ""
	echo "Note: Some processes may take a moment to fully terminate"
}

show_usage() {
	echo "Usage: $0 [service_name|all] [port]"
	echo ""
	echo "Services:"
	echo "  model-adapter (port 8081)"
	echo "  prompt-service (port 8082)"
	echo "  retrieval-service (port 8083)"
	echo "  agent-service (port 8084)"
	echo "  orchestrator (port 8085)"
	echo ""
	echo "Examples:"
	echo "  $0 all                    # Stop all services"
	echo "  $0 orchestrator           # Stop orchestrator on default port 8085"
	echo "  $0 orchestrator 8000      # Stop service on port 8000"
	echo "  $0 agent-service 8084     # Stop agent-service on port 8084"
	echo ""
	echo "Quick commands:"
	echo "  lsof -ti:8000             # Find process on port"
	echo "  kill \$(lsof -ti:8000)     # Manual kill"
}

if [ -z "$SERVICE_NAME" ]; then
	show_usage
	exit 1
fi

if [ "$SERVICE_NAME" = "all" ]; then
	kill_all_services
else
	kill_service "$SERVICE_NAME" "$PORT"
fi

