
# 使用极小的 Alpine Python 镜像
FROM docker.1ms.run/python:3.13-alpine

WORKDIR /app

# 拷贝脚本
COPY app.py .

# 创建共享目录
RUN mkdir -p /root/hermes_shared

# 设置工作目录为共享目录，这样脚本启动时就在正确的位置
WORKDIR /root/hermes_shared

# 暴露端口
EXPOSE 8083

# 启动服务
CMD ["python", "/app/app.py"]
