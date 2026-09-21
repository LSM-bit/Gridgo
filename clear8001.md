# 查看 8001 端口的进程
Get-NetTCPConnection -LocalPort 8001
# 只杀掉占用 8001 端口的进程（按监听端口精确定位 PID，避免误杀其它 python 进程）
Get-NetTCPConnection -LocalPort 8001 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
# 然后重新启动