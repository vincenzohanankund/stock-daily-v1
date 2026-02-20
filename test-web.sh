#!/bin/bash
# ===================================
# A股/港股/美股 智能分析系统 - 前端测试脚本
# ===================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Node.js 环境
if ! command -v npm &> /dev/null; then
    error "npm 未安装，请先安装 Node.js"
    exit 1
fi

WEB_DIR="apps/dsa-web"

if [ ! -d "$WEB_DIR" ]; then
    error "前端目录 $WEB_DIR 不存在"
    exit 1
fi

cd "$WEB_DIR"

info "正在检查前端依赖..."
if [ ! -d "node_modules" ]; then
    info "正在安装依赖..."
    npm install
else
    info "依赖已存在，跳过安装 (若运行失败请手动执行 npm install)"
fi

info "开始运行前端测试..."
npm test

success "前端测试执行完毕"
