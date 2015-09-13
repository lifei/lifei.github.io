title: 基于Nginx搭建rtmp流媒体服务器
date: 2015-08-03 22:53:06
tags:
---

## 背景

### 什么是`RTMP`？
### `RTMP`解决什么问题？
### `HLS`是什么？它和`RTMP`有什么区别？

## 编译安装

https://github.com/arut/nginx-rtmp-module

```Dockerfile
FROM ubuntu
RUN sed -i 's/http:\/\/archive\.ubuntu\.com\/ubuntu\//http:\/\/mirrors.163.com\/ubuntu\//' /etc/apt/sources.list
RUN sed -i 's/deb-src/# deb-src/' /etc/apt/sources.list
RUN apt-get update
RUN apt-get -y install build-essential libpcre3 libpcre3-dev libssl-dev
RUN apt-get -y install software-properties-common
RUN add-apt-repository -y ppa:kirillshkrogalev/ffmpeg-next
RUN apt-get update
RUN apt-get -y install ffmpeg
RUN apt-get -y remove software-properties-common
RUN apt-get -y autoremove

ADD nginx-1.9.3.tar.gz /tmp/
ADD nginx-rtmp-module.tar.gz /var/lib/
RUN cd /tmp/nginx-1.9.3 && ./configure --with-http_ssl_module \
    --sbin-path=/usr/local/sbin/nginx \
    --pid-path=/var/run/nginx.pid \
    --error-log-path=/dev/stderr \
    --http-log-path=/dev/stdout \
    --conf-path=/etc/nginx/nginx.conf \
    --http-client-body-temp-path=/var/cache/nginx/client_body_temp \
    --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
    --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
    --add-module=/var/lib/nginx-rtmp-module/ && make && make install

COPY nginx.conf /etc/nginx/nginx.conf


VOLUME ["/etc/nginx/sites-enabled", "/etc/nginx/conf.d", "/var/cache/nginx"]
CMD ["nginx", "-g", "daemon off;"]
```
