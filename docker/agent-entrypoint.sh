#!/bin/bash
# Agent Marketplace V2 - Agent启动脚本

set -e

echo "Starting Agent: ${AGENT_NAME:-Unknown}"
echo "Agent ID: ${AGENT_ID:-unknown}"
echo "Platform: ${PLATFORM_WS:-ws://backend:8000/ws/agent}"

# 等待后端就绪
echo "Waiting for backend..."
until curl -sf "${PLATFORM_API:-http://backend:8000}/health" > /dev/null 2>&1; do
    echo "Backend not ready, waiting..."
    sleep 2
done

echo "Backend is ready!"

# 启动Agent
exec python -m agents.agent1
