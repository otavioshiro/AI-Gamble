# 使用官方 Python 镜像作为基础
FROM python:3.11-slim

# 安装 Node.js 和 npm
# 使用国内镜像源加速
RUN sed -i 's#deb.debian.org#mirrors.aliyun.com#g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    # 安装 Node.js
    apt-get install -y curl xz-utils && \
    curl -fsSL "https://npmmirror.com/mirrors/node/v18.17.1/node-v18.17.1-linux-x64.tar.xz" | tar -xJ --strip-components=1 -C /usr/local/

# 设置工作目录
WORKDIR /app

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com


# 复制 package.json 和 package-lock.json 并安装 Node.js 依赖
COPY package.json package-lock.json ./
RUN npm install --registry=https://registry.npmmirror.com

# 复制前端源文件并构建
COPY static ./static
COPY tailwind.config.js .
RUN npm run build

# 复制应用代码
COPY . .

# 复制并设置入口点脚本
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 暴露端口
EXPOSE 8000

# 运行应用
CMD ["entrypoint.sh"]