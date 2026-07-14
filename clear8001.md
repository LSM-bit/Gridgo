# 查看 8001 端口的进程
Get-NetTCPConnection -LocalPort 8001
# 杀掉所有 uvicorn 进程
Get-Process python | Stop-Process -Force
# 然后重新启动