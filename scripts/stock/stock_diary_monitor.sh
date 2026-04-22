#!/bin/bash
# 股票日记网站监控与自动重启脚本

# 配置
SITE_NAME="股票日记网站"
SITE_URL="http://localhost:3000"  # 根据实际情况修改
CHECK_INTERVAL=60  # 检查间隔（秒）
MAX_RETRIES=3      # 最大重试次数
LOG_FILE="/var/log/stock_diary_monitor.log"
PID_FILE="/tmp/stock_diary.pid"
START_SCRIPT="/root/start_stock_diary.sh"  # 启动脚本路径

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查网站是否正常
check_site() {
    # 尝试多种检查方式
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$SITE_URL" 2>/dev/null)
    
    if [ "$response_code" = "200" ] || [ "$response_code" = "301" ] || [ "$response_code" = "302" ]; then
        return 0  # 网站正常
    else
        # 尝试检查进程
        if [ -f "$PID_FILE" ]; then
            local pid=$(cat "$PID_FILE")
            if ps -p "$pid" > /dev/null 2>&1; then
                log "网站进程 $pid 存在，但无法访问 (HTTP $response_code)"
                return 1
            else
                log "网站进程 $pid 不存在"
                return 2
            fi
        else
            log "未找到PID文件，网站可能未运行"
            return 3
        fi
    fi
}

# 启动网站
start_site() {
    log "正在启动 $SITE_NAME..."
    
    if [ -f "$START_SCRIPT" ] && [ -x "$START_SCRIPT" ]; then
        # 使用启动脚本
        nohup "$START_SCRIPT" > /dev/null 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"
        log "启动脚本执行成功，PID: $pid"
        return 0
    else
        # 尝试常见启动方式
        log "启动脚本不存在，尝试常见启动方式..."
        
        # 方式1: Node.js应用
        if [ -f "/root/stock-diary/package.json" ]; then
            cd "/root/stock-diary" || return 1
            nohup npm start > /dev/null 2>&1 &
            local pid=$!
            echo "$pid" > "$PID_FILE"
            log "Node.js应用启动成功，PID: $pid"
            return 0
        fi
        
        # 方式2: Python应用
        if [ -f "/root/stock-diary/app.py" ] || [ -f "/root/stock-diary/main.py" ]; then
            cd "/root/stock-diary" || return 1
            nohup python3 app.py > /dev/null 2>&1 &
            local pid=$!
            echo "$pid" > "$PID_FILE"
            log "Python应用启动成功，PID: $pid"
            return 0
        fi
        
        # 方式3: 静态网站
        if [ -d "/root/stock-diary" ]; then
            cd "/root/stock-diary" || return 1
            nohup python3 -m http.server 3000 > /dev/null 2>&1 &
            local pid=$!
            echo "$pid" > "$PID_FILE"
            log "静态网站启动成功，PID: $pid"
            return 0
        fi
        
        log "错误: 无法找到网站文件"
        return 1
    fi
}

# 停止网站
stop_site() {
    log "正在停止 $SITE_NAME..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid"
            sleep 2
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid"
                log "强制停止进程 $pid"
            else
                log "正常停止进程 $pid"
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # 清理可能残留的进程
    pkill -f "stock.*diary" 2>/dev/null || true
    pkill -f "node.*3000" 2>/dev/null || true
    pkill -f "python.*3000" 2>/dev/null || true
    
    log "网站停止完成"
}

# 主监控循环
monitor_loop() {
    log "开始监控 $SITE_NAME..."
    log "网站URL: $SITE_URL"
    log "检查间隔: ${CHECK_INTERVAL}秒"
    
    local failure_count=0
    
    while true; do
        check_site
        local status=$?
        
        if [ $status -eq 0 ]; then
            # 网站正常
            if [ $failure_count -gt 0 ]; then
                log "网站恢复正常"
                failure_count=0
            fi
        else
            # 网站异常
            ((failure_count++))
            log "网站异常 (状态码: $status), 失败次数: $failure_count"
            
            if [ $failure_count -ge $MAX_RETRIES ]; then
                log "达到最大重试次数，尝试重启网站..."
                stop_site
                sleep 5
                
                if start_site; then
                    log "网站重启成功"
                    failure_count=0
                    sleep 30  # 给网站启动时间
                else
                    log "网站重启失败"
                fi
            fi
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# 创建启动脚本模板
create_start_script() {
    cat > "$START_SCRIPT" << 'EOF'
#!/bin/bash
# 股票日记网站启动脚本
# 请根据实际情况修改

echo "启动股票日记网站..."

# 方式1: Node.js应用
if [ -f "/root/stock-diary/package.json" ]; then
    cd "/root/stock-diary"
    npm install  # 如果需要
    npm start
    exit 0
fi

# 方式2: Python Flask应用
if [ -f "/root/stock-diary/app.py" ]; then
    cd "/root/stock-diary"
    pip install -r requirements.txt  # 如果需要
    python3 app.py
    exit 0
fi

# 方式3: 静态网站
if [ -d "/root/stock-diary" ]; then
    cd "/root/stock-diary"
    python3 -m http.server 3000
    exit 0
fi

echo "错误: 未找到网站文件"
exit 1
EOF
    
    chmod +x "$START_SCRIPT"
    log "创建启动脚本: $START_SCRIPT"
}

# 设置系统服务
setup_systemd_service() {
    local service_file="/etc/systemd/system/stock-diary.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=Stock Diary Website
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/root/start_stock_diary.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable stock-diary.service
    log "系统服务已设置: stock-diary.service"
    log "启用命令: systemctl start stock-diary"
    log "状态检查: systemctl status stock-diary"
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "$1" in
        "start")
            log "手动启动监控..."
            monitor_loop
            ;;
        "stop")
            log "停止监控和网站..."
            stop_site
            pkill -f "stock_diary_monitor.sh" 2>/dev/null || true
            ;;
        "status")
            check_site
            case $? in
                0) echo "网站状态: 正常" ;;
                1) echo "网站状态: 进程存在但无法访问" ;;
                2) echo "网站状态: 进程不存在" ;;
                3) echo "网站状态: 未运行" ;;
            esac
            ;;
        "setup")
            log "设置自动启动..."
            create_start_script
            setup_systemd_service
            ;;
        "restart")
            log "手动重启网站..."
            stop_site
            sleep 2
            start_site
            ;;
        *)
            echo "使用方法: $0 {start|stop|status|setup|restart}"
            echo "  start   启动监控"
            echo "  stop    停止监控"
            echo "  status  检查状态"
            echo "  setup   设置系统服务"
            echo "  restart 手动重启网站"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"